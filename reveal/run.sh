#!/usr/bin/env bash
# Session-start reveal. Fails silently: a broken decoration must never be
# able to hold up the login.
exec "$(dirname "$(readlink -f "$0")")/reveal" >/dev/null 2>&1
