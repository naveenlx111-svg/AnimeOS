#!/usr/bin/env bash
# Session-start reveal. Fails silently: a broken decoration must never be
# able to hold up the login.
exec qml6 "$(dirname "$(readlink -f "$0")")/Reveal.qml" >/dev/null 2>&1
