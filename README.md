# LITT: Low-Intrusion Time Tracker

LITT (or `tt` for short) is intended to be a simple, fast (as in workflow), and terse time tracking tool with a CLI frontend and a simple JSON file as a backend database. It was spawned out of a dissatisfaction with existing time tracking tools that were primarily web based, and required too many different input mechanisms (keyboard, mouse, app, etc...).

## Is this right for me?

Using `tt` can be extremely terse, and could even be bound to a keyboard macro button. At it's shortest, it can be used as a simple stopwatch that logs to a file.

The following command will start a stopwatch, if one isn't currently running, or stop the currently running stopwatch.

```
tt sw
```

Note that since you have not supplied any information about _what_ you were doing during that time, it cannot fill it in however you can amend these recorded time periods after the fact with more detail. If you want to supply information about what you are doing, you can either supply a description explicitly, as in:

```
tt sw "Writing documentation"
```

Or make use of aliases which allow you to match a set of tags, a description, and other information to a string. You can create an alias with the following:

```
tt alias --key dev.docs --tag Development --tag Documentation --description "Writing documentation for dev work"
```

Note that the previous `tt` command example is actually doing more than just adding a description. It is checking to see if the supplied string matches an alias and, if so, using the values associated with that alias key; if no alias is found matching that key, then the string is treated as a task description.

You can use aliases with the exact same command syntax as above:

```
tt sw dev.docs
```

That's the general idea. If these examples seem like this is a tool you're interested in trying, give the rest of the detail use cases a read.

## Installation

LITT makes use of the Python `dateparser` package, so you'll need to install that either from pip or your OS packages.

The script is Python2.7/Python3 compatible.

The time tracking DB, as well as the configuration files, are stored in `~/.litt`.

## Configuration

`tt` accepts a few global configuration parameters, which are set persistently using `tt config`, but can be set on a per-use basis by supplying the same options to any other `tt` command (that is, the following options are accepted by any `tt` command, and if given explicitly will override the persistent settings).

- `--output-format`
    - Accepts one of: `json`, `json-compact`, `human`
    - Defaults to: `json-compact`

## Basic Functionality

The usage of `tt` is pretty straight forward:

- You can use it as a stopwatch with at most one concurrent interruption
  - Example: You start a stopwatch (`tt start`) to work on documentation, but you get an urgent bug report that you want to respond to. Instead of stopping (`tt stop`) and restarting your stopwatch, you can interrupt (`tt interrupt` or `tt i`) it to respond to the bug report, and then resume (`tt resume` or `tt r`) the stopwatch.
  - The choice of not supporting arbitrarily nested interruptions is a workflow one, to encourage less churn in task selection.
- You can use it as a ledger to record time after the fact.
  - Example: You keep track of time on a handwritten notepad to take between client sites. At the end of the day, you can record all of those time allocates with `tt track`

  There are two additional commands that allow you to edit time records (`tt amend`) and create aliases for commonly used tasks (`tt alias`) that round out the functionality.

  Viewing tracked data is done with `tt ls` which allows for filtering, viewing, and optionally saving the data for use with another application.

  **Note: To support terse interaction, all options have short and long forms, and in many cases positional arguments are supported where the meaning is either unambiguous or can be derived.**

## Anatomy of a Time Record

A time record, as tracked by `tt`, has several properties:

- `Identifier`: The string that uniquely identifies this time record, allowing it to be uniquely identified when amending properties. This is decided at commit-time (see `CommitTime`) and can either be user-provided, or is auto-generated. This is only used by the user to amend the time record after it has been committed, and can safely be left as auto-generated unless there is a specific reason for explicit IDs.
- `StartTime`: The unix timestamp that the time record starts.
- `EndTime`: The unix timestamp that the time record ends.
- `CommitTime`: The unix timestamp that the time record was committed to the persistent ledger.
- `Description`: A short one-line description of the work performed.
- `Detail`: A detailed description of the work performed.
- `Tags`: A collection of strings that are associated with this time record, useful for filtering, grouping, and aggregating. Any number of tags can be attached to a time record.
- `StructuredData`: A string of data that has some structural interpretation. Internally to `tt` this is just saved as a base64, but this is useful if you have applications that interface with `tt` (such as storing TaskWarrior task IDs, or other information).

## Using `tt` as a Stopwatch

The stopwatch mode of operation of `tt` assumes that it is being used in-line with workflows, and so the timestamps of events are all taken to be the time the command is run. If this is incorrect, the resulting time records can be amended (see [Amending Time Records](#amending-time-records)).

Three are several commands that control the behaviour of `tt` when using it as a stopwatch.

- `tt` prints the status of the currently active stopwatch and, if active, the interrupt timer.
- `tt start` starts a stopwatch, and will error (gracefully) if a stopwatch is already running.
- `tt stop` stops a currently running stopwatch, and will error (gracefully) if no stopwatch is currently running.
- `tt sw` will start a stopwatch if one is not running, and will stop a stopwatch if one is currently running.
- `tt interrupt` (`tt i`) will interrupt a currently running stopwatch (if one is running, otherwise it will act as an alias to `tt start`), which pauses the running stopwatch and starts a new one.
- `tt resume` (`tt r`) will stop the stopwatch started by `tt interrupt` and resume the stopwatch (if there was one, otherwise it will act as an alias to `tt stop`) that was running when `tt interrupt` was called.

`tt sw` is a context-aware alias to `tt start` or `tt stop` that will happily do what you tell it to (such as accidentally clobber a running stopwatch if issued by accident), and is provided as a terse alternative for brave users.

`tt start` and `tt stop` are the recommended commands for using the stopwatch, especially to start.

All of the above commands support the following options:

- `-d`/`--description`
- `-t`/`--tag`
- `-D`/`--detail`

`tt start`, `tt interrupt`, and `tt sw` (when starting a stopwatch) are commands that open a new interval and support one positional argument and these additional options:

- `-a`/`--alias`

When provided, the positional argument is checked against the list of known alias keys. If an alias key matching the positional argument is found, then the positional argument is treated as the value of `--alias`. If no alias key matching the positional argument is found, then it is treated as the value of `--description`.

For more on aliases, see the [Aliases](#aliases) section.

`tt stop`, `tt resume`, and `tt sw` (when stopping a stopwatch) are commit-level operations, and options specified with these commands override (or add to, in the case of `--tag`) the values of the options given to the corresponding command that started the current stopwatch (or interruption interval). Additionally these commands support the following options:

- `-i`/`--id`
- `-u`/`--untag`

Note that the `--id` parameter provides an opportunity for the user to explicitly dictate the ID that should be used for this time record, which must be unique among all time records tracked so far.

## Using `tt` as a Ledger

There is only one command for using `tt` as a ledger, `tt track`, which takes all of the same options as `tt start` and `tt stop`, supports the positional argument semantic of `tt start`, and has these additional options:

- `-s`/`--start`
- `-e`/`--end`
- `--dryrun`

`--start` and `--end` take any absolute or relative time or date specification, and their values are parsed by the _dateparser_ Python module. If no timezone is given, then the local timezone is assumed.

`--dryrun` is provided to allow you to see the dates and times that are being parsed from your provided date specifications without committing to record to the ledger.

Note that `--id` has the same interpretation here as it does in `tt stop`.

## Aliases

Aliases are ways of pairing commonly used options (description, detail, tags, etc...) with a shorter, easily remembered key. Recall the example from above:

```
tt alias --key dev.docs --tag Development --tag Documentation --description "Writing documentation for dev work"
```

This alias can now be referenced in any of `tt start`, `tt interrupt`, or `tt sw` (when starting a stopwatch).

When a valid alias key is given to a command, the properties defined by the alias are set first, and if any other options are provided, those values override the value set by the alias. For example, using the above alias:

```
tt start dev.docs -d "Proof-reading documentation"
```

Would produce a time record with the _Development_ and _Documentation_ tags, but instead of the alias' description, the one provided on the command line will be used.

## Amending Time Records

Time records committed to the ledger are not immutable, and changes can be made with `tt amend` which takes the same options as `tt track` without the positional argument. Note that `--id` has a different meaning to `tt amend` as it does in `tt stop`; that is for `tt amend`, the `--id` option is mandatory, and indicates which time record the edits should be applied to.

Values to options given to `tt amend` will **replace** the values on the specified time record with the exception of `--tag` which will **append** to the tags associated with the specified time record.

## Reading the Ledger

Reading records from the ledger can be done with `tt read`, which supports the following options:

- `-i`/`--id`
- `-f`/`--filter`
- `-o`/`--outfile`
- `-c`/`--csv`
- `-w`/`--with-structured-data`
- `--dryrun`

By default, the structured data is not included in the output, however this can be changed with `--with-structured-data` (which leaves it in the base64 encoded form).

If `--id` is given then only the exact specified time record is returned, and any values of `--filter` and the presence of `--csv` are ignored.

The `--csv` option takes no arguments, and will generate a time-sheet-style CSV, with each record on a line, and one column per tag (with marks in the appropriate rows and columns indicating which records were tagged in which way). This overrides any setting of `--output-format`, either persistent or on the command line.

The `--filter` option can be specified multiple times, and records **must match all filters to be contained in the output**. The `--filter` options takes one of the following filters:

- `tag: {comma separated list of tags treated as OR}`
- `start: {<,<=,==,>=,>}{timespec}`
- `end: {<,<=,==,>=,>}{timespec}`
- `description: {regular expression the description should match}`
- `detail: {regular expression the description should match}`

As with `tt track`, the timespecs passed to these filters are parsed by `dateparser`, and so can be relative or absolute. As with `tt track`, `--dryrun` is provided to provide transparency in how your timespecs are being parsed.