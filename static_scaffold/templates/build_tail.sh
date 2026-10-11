
BIN="$DIST/bin/__BIN__"
echo
echo ">>> done: $BIN"
__VERSION_CMD__
if [ "$OS" = Linux ]; then
  if [ "$STATIC" = 1 ]; then
    # static musl libc embeds the loader path as a string, so check for an interpreter header.
    if readelf -l "$BIN" | grep -q INTERP; then
      echo "WARNING: __BIN__ references a dynamic loader, not fully static" >&2
    else
      echo "fully static"
    fi
  else
    echo "only glibc is dynamic"
  fi
else
  otool -L "$BIN"
  # only the system may supply libraries, not Homebrew or /usr/local
  if otool -L "$BIN" | tail -n +2 | grep -q -v -E '^[[:space:]]+(/usr/lib/|/System/)'; then
    echo "ERROR: __BIN__ links a library that is not part of macOS" >&2
    exit 1
  fi
fi
