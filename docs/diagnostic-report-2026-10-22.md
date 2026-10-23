# Diagnostic report: panel cannot be dismissed

Date: 2026-10-22. Plugin 1.1.0 (`46f62ad`), Omarchy 4.0.6-1.

## Summary

On a third-party bar widget, the panel could not be closed by outside click, `Escape`, or the `close` IPC call. `close()` threw before it reached `controller.hide()`.

Source of the report: GitHub pull request #1 on the mirror (`alexschexc/omarchy-pan-orthodox-daily`), from an outside contributor. It is a pull request, not an issue. This repository on GitLab is canonical.

## Root cause

Third-party widgets are handed `PluginBarApi` (`/usr/share/omarchy/shell/Ui/PluginBarApi.qml`), not the bar. There, `centerHoverRevealSuppressed` is `readonly` and the setter is the method `setCenterHoverRevealSuppressed()`.

`Panel.qml` did this:

```qml
function close() {
  root.setCenterHoverRevealSuppressed(false)   // threw TypeError
  root.controller.hide()                       // never reached
}
```

and `setCenterHoverRevealSuppressed` assigned to the property whenever `"centerHoverRevealSuppressed" in root.bar` was true, which it is on the facade.

Every dismissal path reaches that function:
- `Escape`: `PanelKeyCatcher.closeRequested` calls `root.close()`.
- Outside click: `KeyboardPanel` `dismissArea` calls `KeyboardPanel.close()`, which calls `owner.close()`, which is the widget's `close()` and then the panel's.
- IPC `close`/`hide`/`toggle`: `Panel.qml` calls `root.close()`.

`open()` made the same call inside `Qt.callLater`, so the hover-reveal suppression never happened either.

## Reproduction

Isolated QML mirroring the facade (read-only property plus setter method), run with `qml -a core`:

| Case | Result |
| --- | --- |
| Old code, facade | `TypeError: Cannot assign to read-only property "centerHoverRevealSuppressed"`, panel still shown |
| New code, facade | panel hidden, suppression cleared |
| New code, first-party bar (writable property, no setter) | panel hidden, suppression cleared |
| New code, no bar | panel hidden |

Not reproduced against the live shell: the running shell had already loaded a working tree that contained the setter-method change. A shell restart (`omarchy restart shell`) is needed to exercise the final code.

## Changes

1. `close()` hides the panel first and clears the hover-reveal flag second.
2. `setCenterHoverRevealSuppressed()` prefers the setter method, falls back to property assignment, and catches and logs any error, so cosmetic bookkeeping can never abort `open()` or `close()`.
3. `manifest.json` gains `homepage`, `repository` and `bugs`, all pointing to GitLab. `omarchy plugin validate` accepts them.
4. `README.md` gains "Reporting problems", and `AGENTS.md` tells an agent on another machine to report to GitLab, what to collect, and not to use GitHub.

## Other observations (not changed)

- `orthocalFetchScript` and `saintImageScript` are built from a hardcoded `~/.config/omarchy/plugins/<id>/` path. If a plugin is ever installed elsewhere, the scripts would not be found. `Qt.resolvedUrl` would avoid that. Unverified on other installs.
- The user agent strings still read "Omarchy Orthodox Daily/1.0" and carry no contact for this project.
- There are no automated tests for the QML. The checks above are manual.
- GitHub pull request #1 duplicates the two hunks in this change. It needs a decision from the maintainer; nothing was posted there.
- `manifest.json` is still `1.1.0`. A patch bump to `1.1.1` is the maintainer's call.

## Verification status

| Check | Result |
| --- | --- |
| `omarchy plugin validate .` | pass |
| `manifest.json` parses | pass |
| Isolated QML repro (table above) | pass |
| `qmllint` | inconclusive: exits 255 on unmodified HEAD too (cannot resolve `qs.*` imports) |
| Live shell, outside click and `Escape` | not run; needs shell restart and a real pointer |
