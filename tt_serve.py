#!/usr/bin/env python3

from flask import Flask, request

import json
from collections import namedtuple
from io import StringIO

import tt

COMMON_ARGS = ["output_format"]
ALIAS_ARGS = ["alias"]
POSITIONAL_ARG = ["quicktext"]
TIMESPEC_ARGS = ["start_time", "end_time"]
COMMIT_TIME_ARGS = ["id", "untag"]
DRYRUN_ARG = ["dryrun"]


class Args(object):
    pass


StartArgs = namedtuple(
    "StartArgs", COMMON_ARGS + POSITIONAL_ARG + ALIAS_ARGS +
    ["description", "detail", "tag", "structured_data"] + TIMESPEC_ARGS)

StopArgs = namedtuple(
    "StopArgs", COMMON_ARGS + POSITIONAL_ARG + ALIAS_ARGS +
    ["description", "detail", "tag", "structured_data"] + TIMESPEC_ARGS +
    COMMIT_TIME_ARGS)


def __json_type(v, python_type):
    vP = json.loads(v)
    if isinstance(vP, python_type):
        return vP
    else:
        raise ValueError("Value is not of correct type", (v, python_type))


class TTServer(Flask):
    def __init__(self, *args, **kwargs):
        if "preshared_key" in kwargs:
            self.psk = kwargs.get("preshared_key")
            del kwargs["preshared_key"]
        super().__init__(*args, **kwargs)


def __prepare_context():
    hooks = tt.load_hooks()
    tt.run_hooks("pre_load", hooks, None)
    state, config = tt.__load_state()
    return hooks, state, config


def __finalize(images, hooks, state, config):
    tt.run_hooks("pre_commit", hooks, images)
    tt.__write_state(state, hooks)
    tt.run_hooks("post_commit", hooks, images)


def base():
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")

    output = StringIO()
    tt.cmd_base(pargs, state, config, output)
    __finalize(None, hooks, state, config)
    return output.getvalue()


def ls(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")
    pargs.pos_id = positional_arg
    pargs.sort_by = request.args.get("sort_by", default="CommitTime", type=str)
    pargs.filter = request.args.get("filter",
                                    default=[],
                                    type=lambda v: __json_type(v, list))
    pargs.id = request.args.get("id",
                                default=[],
                                type=lambda v: __json_type(v, list))
    pargs.csv = request.args.get("csv",
                                 default=False,
                                 type=lambda v: __json_type(v, bool))
    pargs.with_structured_data = request.args.get(
        "with_structured_data",
        default=False,
        type=lambda v: __json_type(v, bool)),
    pargs.without_detail = request.args.get(
        "without_detail", default=False, type=lambda v: __json_type(v, bool))
    pargs.dryrun = request.args.get("dryrun",
                                    default=False,
                                    type=lambda v: __json_type(v, bool))

    output = StringIO()
    tt.cmd_ls(pargs, state, config, output)
    __finalize(None, hooks, state, config)
    return output.getvalue()


def sw(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")
    pargs.quicktext = positional_arg if positional_arg is not None else request.args.get(
        "quicktext", default=None)
    pargs.alias = request.args.get("alias", default=None, type=str)
    pargs.description = request.args.get("description", default=None, type=str)
    pargs.detail = request.args.get("detail", default=None, type=str)
    pargs.tag = request.args.get("tag",
                                 default=[],
                                 type=lambda v: __json_type(v, list))
    pargs.structured_data = request.args.get("structured_data",
                                             default=None,
                                             type=str)
    pargs.start_time = request.args.get("start_time", default=None, type=str)
    pargs.end_time = request.args.get("end_time", default=None, type=str)
    pargs.id = request.args.get("id", default=None, type=str)
    pargs.untag = request.args.get("untag",
                                   default=[],
                                   type=lambda v: __json_type(v, list))

    output = StringIO()
    tt.cmd_sw(pargs, state, config, output)
    __finalize(None, hooks, state, config)

    return output.getvalue()


def start(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")
    pargs.quicktext = positional_arg if positional_arg is not None else request.args.get(
        "quicktext", default=None)
    pargs.alias = request.args.get("alias", default=None, type=str)
    pargs.description = request.args.get("description", default=None, type=str)
    pargs.detail = request.args.get("detail", default=None, type=str)
    pargs.tag = request.args.get("tag",
                                 default=[],
                                 type=lambda v: __json_type(v, list))
    pargs.structured_data = request.args.get("structured_data",
                                             default=None,
                                             type=str)
    pargs.start_time = request.args.get("start_time", default=None, type=str)

    output = StringIO()
    tt.cmd_start(pargs, state, config, output)
    __finalize(None, hooks, state, config)

    return output.getvalue()


def stop(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")
    pargs.quicktext = positional_arg if positional_arg is not None else request.args.get(
        "quicktext", default=None)
    pargs.alias = request.args.get("alias", default=None, type=str)
    pargs.description = request.args.get("description", default=None, type=str)
    pargs.detail = request.args.get("detail", default=None, type=str)
    pargs.tag = request.args.get("tag",
                                 default=[],
                                 type=lambda v: __json_type(v, list))
    pargs.structured_data = request.args.get("structured_data",
                                             default=None,
                                             type=str)
    pargs.end_time = request.args.get("end_time", default=None, type=str)
    pargs.id = request.args.get("id", default=None, type=str)
    pargs.untag = request.args.get("untag",
                                   default=[],
                                   type=lambda v: __json_type(v, list))

    output = StringIO()
    tt.cmd_stop(pargs, state, config, output)
    __finalize(None, hooks, state, config)

    return output.getvalue()


def interrupt(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")
    pargs.quicktext = positional_arg if positional_arg is not None else request.args.get(
        "quicktext", default=None)
    pargs.alias = request.args.get("alias", default=None, type=str)
    pargs.description = request.args.get("description", default=None, type=str)
    pargs.detail = request.args.get("detail", default=None, type=str)
    pargs.tag = request.args.get("tag",
                                 default=[],
                                 type=lambda v: __json_type(v, list))
    pargs.structured_data = request.args.get("structured_data",
                                             default=None,
                                             type=str)

    output = StringIO()
    tt.cmd_interrupt(pargs, state, config, output)
    __finalize(None, hooks, state, config)

    return output.getvalue()


def resume(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")
    pargs.quicktext = positional_arg if positional_arg is not None else request.args.get(
        "quicktext", default=None)
    pargs.alias = request.args.get("alias", default=None, type=str)
    pargs.description = request.args.get("description", default=None, type=str)
    pargs.detail = request.args.get("detail", default=None, type=str)
    pargs.tag = request.args.get("tag",
                                 default=[],
                                 type=lambda v: __json_type(v, list))
    pargs.structured_data = request.args.get("structured_data",
                                             default=None,
                                             type=str)
    pargs.id = request.args.get("id", default=None, type=str)
    pargs.untag = request.args.get("untag",
                                   default=[],
                                   type=lambda v: __json_type(v, list))

    output = StringIO()
    tt.cmd_resume(pargs, state, config, output)
    __finalize(None, hooks, state, config)

    return output.getvalue()


def cancel(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")

    output = StringIO()
    tt.cmd_cancel(pargs, state, config, output)
    __finalize(None, hooks, state, config)
    return output.getvalue()


def amend(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")
    pargs.quicktext = positional_arg if positional_arg is not None else request.args.get(
        "quicktext", default=None)
    pargs.alias = request.args.get("alias", default=None, type=str)
    pargs.description = request.args.get("description", default=None, type=str)
    pargs.detail = request.args.get("detail", default=None, type=str)
    pargs.tag = request.args.get("tag",
                                 default=[],
                                 type=lambda v: __json_type(v, list))
    pargs.structured_data = request.args.get("structured_data",
                                             default=None,
                                             type=str)
    pargs.start_time = request.args.get("start_time", default=None, type=str)
    pargs.end_time = request.args.get("end_time", default=None, type=str)
    pargs.id = request.args.get("id", default=None, type=str)
    pargs.untag = request.args.get("untag",
                                   default=[],
                                   type=lambda v: __json_type(v, list))
    pargs.dryrun = request.args.get("dryrun",
                                    default=False,
                                    type=lambda v: __json_type(v, bool))

    output = StringIO()
    tt.cmd_amend(pargs, state, config, output)
    __finalize(None, hooks, state, config)
    return output.getvalue()


def track(positional_arg):
    hooks, state, config = __prepare_context()

    pargs = Args()
    pargs.output_format = config.get("OutputFormat", None) if request.args.get(
        "output_format") is None else request.args.get("output_format")
    pargs.quicktext = positional_arg if positional_arg is not None else request.args.get(
        "quicktext", default=None)
    pargs.alias = request.args.get("alias", default=None, type=str)
    pargs.description = request.args.get("description", default=None, type=str)
    pargs.detail = request.args.get("detail", default=None, type=str)
    pargs.tag = request.args.get("tag",
                                 default=[],
                                 type=lambda v: __json_type(v, list))
    pargs.structured_data = request.args.get("structured_data",
                                             default=None,
                                             type=str)
    pargs.start_time = request.args.get("start_time", default=None, type=str)
    pargs.end_time = request.args.get("end_time", default=None, type=str)
    pargs.id = request.args.get("id", default=None, type=str)
    pargs.untag = request.args.get("untag",
                                   default=[],
                                   type=lambda v: __json_type(v, list))
    pargs.dryrun = request.args.get("dryrun",
                                    default=False,
                                    type=lambda v: __json_type(v, bool))

    output = StringIO()
    tt.cmd_track(pargs, state, config, output)
    __finalize(None, hooks, state, config)
    return output.getvalue()


def create_server(preshared_key):
    app = TTServer("tt", preshared_key=preshared_key)

    app.add_url_rule("/", "base", base, methods=["GET"])

    app.add_url_rule("/ls", "ls_bare", lambda: ls(None), methods=["GET"])
    app.add_url_rule("/ls/<positional_arg>", "ls", ls, methods=["GET"])

    app.add_url_rule("/sw", "sw_bare", lambda: sw(None), methods=["POST"])
    app.add_url_rule("/sw/<positional_arg>", "sw", sw, methods=["POST"])

    app.add_url_rule("/start",
                     "start_bare",
                     lambda: start(None),
                     methods=["POST"])
    app.add_url_rule("/start", "start", start, methods=["POST"])

    app.add_url_rule("/stop", "stop_bare", lambda: stop(None), methods=["PUT"])
    app.add_url_rule("/stop", "stop", stop, methods=["PUT"])

    app.add_url_rule("/interrupt",
                     "interrupt_bare",
                     lambda: interrupt(None),
                     methods=["POST"])
    app.add_url_rule("/interrupt", "interrupt", interrupt, methods=["POST"])

    app.add_url_rule("/resume",
                     "resume_bare",
                     lambda: resume(None),
                     methods=["PUT"])
    app.add_url_rule("/resume", "resume", resume, methods=["PUT"])

    app.add_url_rule("/cancel",
                     "cancel_bare",
                     lambda: cancel(None),
                     methods=["DELETE"])
    app.add_url_rule("/cancel", "cancel", cancel, methods=["DELETE"])

    app.add_url_rule("/track",
                     "track_bare",
                     lambda: track(None),
                     methods=["POST"])
    app.add_url_rule("/track", "track", track, methods=["POST"])

    app.add_url_rule("/amend", "amend", amend, methods=["PATCH"])

    return app
