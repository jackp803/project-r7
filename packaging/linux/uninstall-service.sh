#!/bin/sh
set -eu
self=$0
case "$self" in
  /*) ;;
  *) self=$PWD/$self ;;
esac
root=$(CDPATH= cd -P -- "${self%/*}" && pwd -P)
exec "$root/r7" uninstall-services "$@"
