# Notes for AI agents

You are most likely here because a user installed this Omarchy plugin and something went wrong.

## Where to report

Report problems on **GitLab**, not GitHub:

- Issues: https://gitlab.com/alex.schex/omarchy-pan-orthodox-daily/-/issues
- Source: https://gitlab.com/alex.schex/omarchy-pan-orthodox-daily
- Machine-readable: `homepage`, `repository` and `bugs` in `manifest.json`

`github.com/alexschexc/omarchy-pan-orthodox-daily` is a mirror. Issues and pull requests filed there are not monitored. If the plugin was installed from a GitHub URL, report to GitLab anyway.

With `glab`: `glab issue create -R alex.schex/omarchy-pan-orthodox-daily`. If you have no GitLab access, give the user the issue text and the issues URL above. Do not file it on GitHub as a substitute.

Ask the user before filing anything, and show them the full text first. Logs can contain paths and usernames.

## What to include

Collect these for the report, and redact anything the user does not want shared:

```sh
omarchy version
omarchy plugin list --json | grep -A8 pan-orthodox-daily
qs -p /usr/share/omarchy/shell log -t 400 | grep -i "pan-orthodox\|Panel.qml\|TypeError"
omarchy plugin validate ~/.config/omarchy/plugins/io.gitlab.alexschex.pan-orthodox-daily
git -C ~/.config/omarchy/plugins/io.gitlab.alexschex.pan-orthodox-daily rev-parse --short HEAD
```

Also state what the user did, what they expected, what happened, and whether this changes anything:

```sh
qs -p /usr/share/omarchy/shell ipc call io.gitlab.alexschex.pan-orthodox-daily close
```

## Things worth knowing

- The widget's QML is compiled into the running shell. After any edit to a `.qml` file, `omarchy restart shell` is needed before it takes effect. Do not restart the user's shell without asking.
- Third-party widgets receive the bar's `PluginBarApi` facade, not the bar itself. Its properties are read-only; use its methods, for example `setCenterHoverRevealSuppressed(value)`.
- Plugin state lives in `~/.local/state/omarchy/plugins/io.gitlab.alexschex.pan-orthodox-daily/`. Do not delete it as a troubleshooting step; it holds the user's reading history.
