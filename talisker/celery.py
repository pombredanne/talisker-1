# Copyright (C) 2016- Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

from future import standard_library
standard_library.install_aliases()
from builtins import *  # noqa

import functools
import os
import time

from werkzeug.local import Local
from talisker import logs, request_id
import talisker.statsd


__all__ = [
    'logging',
    'delay',
    'enable_metrics',
    ]

_local = Local()
_local.timers = {}

def log(func):
    """Add celery specific logging context."""
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        from celery import current_task
        tags = {'task_id': current_task.request.id}
        if 'request_id' in kwargs:
            tags['request_id'] = kwargs.pop('request_id')
        with logs.extra_logging(extra=tags):
            return func(*args, **kwargs)

    return decorator


def delay(task, *args, **kwargs):
    id = request_id.get()
    if id:
        kwargs['request_id'] = id
    return task.delay(*args, **kwargs)


# celery helpers
def _timer(task_name, name, value):
    name = 'celery.{}.{}'.format(task_name, name)
    talisker.statsd.get_client().timing(name, value)


def _counter(name):
    def signal(sender, **kwargs):
        stat_name = 'celery.{}.{}'.format(sender.name, name)
        talisker.statsd.get_client().incr(stat_name)
    return signal


### celery signals for metrics ###

def before_task_publish(sender, body, **kwargs):
    # TODO: find a way to avoid thread locals
    if not hasattr(_local, 'timers'):
        _local.timers = {}
    _local.timers[body['id']] = time.time()


def after_task_publish(sender, body, **kwargs):
    _timer(sender, 'enqueue', (time.time() - _local.timers.pop(body['id'])) * 1000)


def task_prerun(sender, task_id, task, **kwargs):
    task.__talisker_timer = time.time()


def task_postrun(sender, task_id, task, **kwargs):
    _timer(sender.name, 'run', (time.time() - task.__talisker_timer) * 1000)


def enable_metrics():
    """Best effort enabling of celery metrics"""
    try:
        from celery import signals
    except ImportError:
        return

    # these should only be fired on the clients
    signals.before_task_publish.connect(before_task_publish)
    signals.after_task_publish.connect(after_task_publish)

    # these should only be fired on the workers
    signals.task_prerun.connect(task_prerun)
    signals.task_postrun.connect(task_postrun)
    signals.task_retry.connect(_counter('retry'))
    signals.task_success.connect(_counter('success'))
    signals.task_failure.connect(_counter('failure'))
    signals.task_revoked.connect(_counter('revoked'))


def run():
    # these must be done before importing celery.
    logs.configure()
    os.environ['CELERYD_HIJACK_ROOT_LOGGER'] = 'False'
    os.environ['CELERYD_REDIRECT_STDOUTS'] = 'False'

    from celery.__main__ import main
    from celery.signals import setup_logging

    # take control of this signal, which prevents celery from setting up it's
    # own logging
    @setup_logging.connect
    def setup_celery_logging(**kwargs):
        # TODO: maybe add process id to extra?
        pass

    enable_metrics()
    main()
