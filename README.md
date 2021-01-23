# LITT: Low-Intrusion Time Tracker

LITT (or `tt` for short) is intended to be a simple, fast (as in workflow), and terse time tracking tool with a CLI frontend and a simple JSON file as a backend database. It was spawned out of a dissatisfaction with existing time tracking tools that were primarily web based, and required too many different input mechanisms (keyboard, mouse, app, etc...).

## Is this right for me?

Using `tt` can be extremely terse, and could even be bound to a keyboard macro button. At it's shortest, it can be used as a simple stopwatch that logs to a file.

The following command will start a stopwatch, if one isn't currently running, or stop the currently running stopwatch.

```shell
tt sw
```

Note that since you have not supplied any information about _what_ you were doing during that time, it cannot fill it in however you can amend these recorded time periods after the fact with more detail. If you want to supply information about what you are doing, you can either supply a description explicitly, as in:

```shell
tt sw "Writing documentation"
```

Or make use of aliases which allow you to match a set of tags, a description, and other information to a string. You can create an alias with the following:

```shell
tt alias --key dev.docs --tag Development --tag Documentation --description "Writing documentation for dev work"
```

Note that the previous `tt sw` command example is actually doing more than just adding a description. It is checking to see if the supplied string matches an alias key and, if so, using the values associated with that alias; if no alias is found matching that key, then the string is treated as a task description.

You can use aliases with the exact same command syntax as above:

```shell
tt sw dev.docs
```

That's the general idea. If these examples seem like this is a tool you're interested in trying, give the rest of the detailed use cases a read.

## Installation

LITT makes use of the Python `dateparser` package, so you'll need to install that either from pip or your OS packages.

Full package dependencies are in [requirements.txt](requirements.txt).

The time tracking DB, as well as the configuration files, are stored in `~/.litt` on Linux, and `%HOMEDRIVE%\%HOMEPATH\.litt` on Windows.

## Configuration

`tt` accepts a few global configuration parameters, which are set persistently using `tt config`, but can be set on a per-use basis by supplying the same options to any other `tt` command (that is, the following options are accepted by any `tt` command, and if given explicitly will override the persistent settings).

- `--output-format`
  - Accepts one of: `json`, `json-compact`, `yaml`
  - Defaults to: `json-compact`
  - Note: `yaml` output is only available if the PyYAML package is installed, and is dynamically detected based on an attempt to import the package.

## Basic Functionality

The usage of `tt` is pretty straight forward:

- You can use it as a stopwatch with at most one concurrent interruption
  - Example: You start a stopwatch (`tt start`) to work on documentation, but you get an urgent bug report that you want to respond to. Instead of stopping (`tt stop`) and restarting your stopwatch, you can interrupt (`tt interrupt` or `tt i`) it to respond to the bug report, and then resume (`tt resume` or `tt r`) the stopwatch.
  - The choice of not supporting arbitrarily nested interruptions is a workflow one, to encourage less churn in task selection.
- You can use it as a ledger to record time after the fact.
  - Example: You keep track of time on a handwritten notepad to take between client sites. At the end of the day, you can record all of those time allocations with `tt track`

There are two additional commands that allow you to edit time records (`tt amend`) and create aliases for commonly used tasks (`tt alias`) that round out the functionality.

Viewing tracked data is done with `tt ls` which allows for filtering, viewing, sorting (sometimes, based on the chosen output format) and optionally saving the data for use with another application.

**Note: To support terse interaction, all options have short and long forms, and in many cases positional arguments are supported where the meaning is either unambiguous or can be derived.**

## Advanced functionality

The Python script supports the execution of arbitrary executables at specific points in the logic, called _hooks_. See the section on [Hooks](#hooks) for more information.

## Anatomy of a Time Record

A time record, as tracked by `tt`, has several properties:

- `Identifier`: The string that uniquely identifies this time record, allowing it to be uniquely identified when amending properties. This is decided at commit-time (see `CommitTime`) and can either be user-provided, or is auto-generated. This is only used by the user to amend the time record after it has been committed, and can safely be left as auto-generated unless there is a specific reason for explicit IDs.
- `StartTime`: The unix timestamp that the time record starts.
- `EndTime`: The unix timestamp that the time record ends.
- `CommitTime`: The unix timestamp that the time record was committed to the persistent ledger.
- `Description`: A short one-line description of the work performed.
- `Detail`: A detailed description of the work performed.
- `Tags`: A collection of strings that are associated with this time record, useful for filtering, grouping, and aggregating. Any number of tags can be attached to a time record.
- `StructuredData`: A string of data that has some structural interpretation. Internally to `tt` this is just saved as a base64 string, but this is useful if you have applications that interface with `tt` (such as storing TaskWarrior task IDs, or other information).

## Using `tt` as a Stopwatch

The stopwatch mode of operation of `tt` assumes that it is being used in-line with workflows, and so the timestamps of events are all taken to be the time the command is run. If this is incorrect, the resulting time records can be amended (see [Amending Time Records](#amending-time-records)).

Three are several commands that control the behaviour of `tt` when using it as a stopwatch.

- `tt` prints the status of the currently active stopwatch and, if active, the interrupt timer.
- `tt start` starts a stopwatch, and will error (gracefully) if a stopwatch is already running.
- `tt stop` stops a currently running stopwatch, and will error (gracefully) if no stopwatch is currently running.
- `tt sw` will start a stopwatch if one is not running, and will stop a stopwatch if one is currently running.
- `tt interrupt` (`tt i`) will interrupt a currently running stopwatch (if one is running, otherwise it will act as an alias to `tt start`), which pauses the running stopwatch and starts a new one.
- `tt resume` (`tt r`) will stop the stopwatch started by `tt interrupt` and resume the stopwatch (if there was one, otherwise it will act as an alias to `tt stop`) that was running when `tt interrupt` was called.
- `tt cancel` will top the stopwatch (or interruption, if one is running) without committing the record to the ledger (effectively discarding the time). If no stopwatch is running, this operation does nothing. If an interruption is running, the interruption is canceled as though `tt interrupt` was never issued (but otherwise leaves the stopwatch intact). It takes no options.

`tt sw` is a context-aware alias to `tt start` or `tt stop` that will happily do what you tell it to (such as accidentally clobber a running stopwatch if issued by accident), and is provided as a terse alternative for brave users.

`tt start` and `tt stop` are the recommended commands for using the stopwatch, especially to start.

All of the above commands support the following options as well as exactly one positional argument:

- `-d`/`--description`
- `-t`/`--tag`
- `-D`/`--detail`
- `-S`/`--structured-data`
- `-a`/`--alias`

When provided, the positional argument is checked against the list of known alias keys. If an alias key matching the positional argument is found, then the positional argument is treated as the value of `--alias`. If no alias key matching the positional argument is found, then it is treated as the value of `--description`.

For more on aliases, see the [Aliases](#aliases) section.

`tt stop`, `tt resume`, and `tt sw` (when stopping a stopwatch) are commit-level operations, and options specified with these commands override (or add to, in the case of `--tag`) the values of the options given to the corresponding command that started the current stopwatch (or interruption interval). When the positional argument is provided to these commands, the interpretation is the same as in other stopwatch commands. Additionally these commands support the following options:

- `-i`/`--id`
- `-u`/`--untag`

Note that the `--id` parameter provides an opportunity for the user to explicitly dictate the ID that should be used for this time record, which must be unique among all time records tracked so far.

## Using `tt` as a Ledger

There is only one command for using `tt` as a ledger, `tt track`, which takes all of the same options as `tt start` and `tt stop`, supports the positional argument semantic of `tt start`, and has these additional options:

- `-s`/`--start`
- `-e`/`--end`
- `--dryrun`

`--start` and `--end` take any absolute or relative time or date specification, and their values are parsed by the _dateparser_ Python module. If no timezone is given, then the local timezone is assumed. At least one of `--start` and `--end` must be specified, and if only one is provided then the other is assumed to be the time the command is invoked. It is an error for the value of `--end` to precede (or equal) the value of `--start`.

`--dryrun` is provided to allow you to see the dates and times that are being parsed from your provided date specifications without committing to record to the ledger.

Note that `--id` has the same interpretation here as it does in `tt stop`.

Since `tt interrupt` and `tt resume` are only used with stopwatch time tracking, there is no way to insert interruptions to a block of time added with `tt track`. See the note about [Mutating History](#mutating-history) for suggestions on how you might go about adding interruptions to these blocks of time manually.

## Aliases

Aliases are ways of pairing commonly used options (description, detail, tags, etc...) with a shorter, easily remembered key. Recall the example from above:

```shell
tt alias --key dev.docs --tag Development --tag Documentation --description "Writing documentation for dev work"
```

This alias can now be referenced in any of `tt start`, `tt interrupt`, or `tt sw` (when starting a stopwatch).

When a valid alias key is given to a command, the properties defined by the alias are set first, and if any other options are provided, those values override the value set by the alias. For example, using the above alias:

```shell
tt start dev.docs -d "Proof-reading documentation"
```

Would produce a time record with the _Development_ and _Documentation_ tags, but instead of the alias' description, the one provided on the command line will be used.

To view all aliases configured, use `tt alias` without arguments, and to replace an alias run with key _AKey_, use `tt alias --key AKey {Options}`. To remove an alias with key _AKey_, simply overwrite it with a new alias that specifies no options (i.e. `tt alias --key AKey`).

## Amending Time Records

Time records committed to the ledger are not immutable, and changes can be made with `tt amend` which takes the same options as `tt track` without the positional argument. Note that `--id` has a different meaning to `tt amend` as it does in `tt stop`; that is for `tt amend`, the `--id` option is mandatory, and indicates which time record the edits should be applied to.

Values to options given to `tt amend` will **replace** the values on the specified time record with the exception of `--tag` which will **append** to the tags associated with the specified time record. Any values set in the specified record that are not explicitly overridden on the `tt amend` command line will be left unmodified.

### Mutating History

Note that LITT takes some pointers from Mercurial and does not include significant tools for editing history in complex or detailed ways. For example, interruptions to stopwatch tracked time periods cannot be edited with `tt amend`. Since the authoritative ledger is a JSON file, if you need to do complex edits to history you will want to do so with other tools (such as `jq`), or a text editor.

## Reading and Displaying the Ledger

Reading records from the ledger can be done with `tt ls`, which supports the following options:

- `-i`/`--id`
- `-s`/`--sort-by`
- `-f`/`--filter`
- `-c`/`--csv`
- `-w`/`--with-structured-data`
- `-D`/`--without-detail`
- `--dryrun`

Sorting with `--sort-by` allows the records to be sorted by some key that is present in a standard record _only when the output format is not one of `json`/`json-compact`/`yaml`_. This is because those formats output a dictionary that keys on record ID, and there is no guarantee that serializing that structure will remain ordered on import and export. When printing the data as a CSV or in human-readable form, the sorting works as expected. By default, records are sorted by `CommitTime`.

By default, the structured data is not included in the output, however this can be changed with `--with-structured-data` (which leaves it in the base64 encoded form). Similarly, the `--without-detail` option will omit the detailed text field (`Detail`) from the output, useful for summary tables or reports where the CSV output is being consumed directly (and not being send to another application for processing.)

If `--id` is given then only the exact specified time record is returned, and any values of `--filter` and the presence of `--csv` are ignored.

The `--csv` option takes no arguments, and will generate a time-sheet-style CSV, with each record on a line, and one column per tag (with marks in the appropriate rows and columns indicating which records were tagged in which way). This overrides any setting of `--output-format`, either persistent or on the command line.

The `--filter` option can be specified multiple times, and records **must match all filters to be contained in the output (that is separate filters are combined with a logical AND)**. The `--filter` options takes JSON documents that describe the filters, with conditions specified in the same JSON documenting being combined with a logical OR (that is, a record matching ANY condition in a single `--filter` expression will be returned, but final results must pass every expression provided with a `--filter` option)

```json
{
  "Tags": [ "string", ... ],
  "StartTime": [
    {
      "Condition": "<"|"<="|"=="|">="|">"|"!=",
      "Timespec": "string"
    },
    ...
  ],
  "EndTime": [
    {
      "Condition": "<"|"<="|"=="|">="|">"|"!=",
      "Timespec": "string"
    },
    ...
  ],
  "Description": [ r"regex", ... ],
  "Detail": [ r"regex", ... ]
}
```

For the tag-based filtering, for a given record to match, the set of tags attached to the record must have a non-empty intersection with the given list of tags, or the two sets must be equal (this permits finding untagged records by asking for an empty tag list).

For regular expression based matching, the python `re.search` function is used, which allows matching patterns anywhere in the given string if no anchors are specified.

As with `tt track`, the timespecs passed to these filters are parsed by `dateparser`, and so can be relative or absolute. As with `tt track`, `--dryrun` is provided to provide transparency in how your timespecs are being parsed.

### Examples

Find all records, displayed human-readably, and sorted by the time they ended.

```shell
tt --output-format human ls --sort-by EndTime
```

Find all of the untagged records.

```shell
tt ls --filter '{"Tags": []}'
```

Find all of the records tagged with both *Personal* and *Gardening*:

```shell
tt ls --filter '{"Tags": ["Personal"])' --filter '{"Tags": ["Gardening"]}'
```

Finding all of the records tagged with *Work* since the start of the work week, not counting anything in progress.

```shell
tt ls --filter '{"StartTime":[{"Condition": ">=", "Timespec": "monday"}]}' \
      --filter '{"EndTime":[{"Condition": "<=", "Timespec": "now"}]}' \
      --filter '{"Tags": ["Work"]}'
```

## Hooks

Hooks are executable files placed in the subdirectories of `~/.litt/hooks`, where the subdirectory is named for the hook event that it should be invoked on. Files found in a hook directory are executed in lexicographical order. When hook events are fired and executables are invoked, the hook event name is passed as the first, and only, command line parameter. Additionally, any contextual information is passed in as JSON on stdin; which information this is is indicated below. Supported hook events are:

- `pre_load`: Before the JSON DB file is loaded from disk
  - Context: `null`
- `pre_commit`: After all changes are made to the state, but before the state is written to disk.
  - Context: The old and new images of any changed items.
    - For Aliases (if the OldImage value is `null`, then the alias did not exist before this command; if the NewImage value is `null` then the alias was deleted by the command run):

    ```json
    {
      "OldImage": {
        "AliasKey": {
          ...<properties>
        }
      },
      "NewImage": {
        "AliasKey": {
          ...<properties>
        }
      }
    }
    ```

    - For Records (if the OldImage value is `null`, then the alias did not exist before this command; if the NewImage value is `null` then the alias was deleted by the command run):

    ```json
    {
      "OldImage": {
        "RecordId": {
          ...<properties>
        }
      },
      "NewImage": {
        "RecordId": {
          ...<properties>
        }
      }
    }
    ```

- `post_commit`: After all changes are made to the state, and after the state is written to disk.
  - Context: Same as `pre_commit`
- `pre_config_write`: After all changes are made to the persistent configuration, but before the config is written to disk.
  - Context: `null`
- `post_config_write`: After all changes are made to the persistent configuration, and after the config is written to disk.
  - Context: `null`
