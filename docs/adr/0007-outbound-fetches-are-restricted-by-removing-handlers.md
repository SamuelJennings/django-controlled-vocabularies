# ADR 0007 — Outbound fetches are restricted by removing capability, not by checking afterwards

**Status:** accepted

## Decision

Every outbound fetch this package makes goes through an opener that carries handlers for `http` and
`https` and nothing else. A URL of any other scheme fails because there is no code able to open it,
not because a check rejected it.

The opener is constructed as an `OpenerDirector` with its handlers added by hand:
`HTTPHandler`, `HTTPSHandler`, `HTTPRedirectHandler`, `HTTPErrorProcessor`, `UnknownHandler`,
`HTTPDefaultErrorHandler`.

It is **not** built with `urllib.request.build_opener`. That function merges its own defaults for
every protocol not overridden by an instance of the same default class, so
`build_opener(HTTPHandler, HTTPSHandler, HTTPRedirectHandler, HTTPErrorProcessor)` still carries a
live `FTPHandler`, `FileHandler` and `DataHandler`. The last two entries above are what make an
unhandled scheme and a non-2xx status raise, rather than `open()` returning `None`.

Transfers are also bounded by a read timeout and a total byte ceiling.

## Why

The operator chooses the address they type. They do not choose where a redirect goes — the remote
server does. Python's own redirect handler permits `http`, `https` and `ftp`, so a server can move a
request onto a protocol the operator never named.

The intuitive defence is to inspect the response's final URL and refuse it. That does not work: the
response object only exists once urllib has followed the redirect and pulled the body, so by the
time the check runs the connection has been made and the transfer has happened. The check reports a
breach that already occurred.

Removing the capability moves the failure earlier than any check can be placed. There is no handler,
so there is no connection.

The `build_opener` detail is recorded here rather than left as a code comment because it is the
kind of thing that gets "simplified" back. The call looks like it constructs an opener from exactly
the handlers named, reads as though it does, and does not. It was caught by a test that redirected
to an unroutable FTP address and observed the request reach ftplib's connect and time out there —
a real network call, from an opener that appeared to have no FTP support.

The size ceiling exists for a related reason. The timeout bounds each socket read, not the transfer,
so a server that answers slowly but continuously never trips it, and nothing otherwise bounds how
much is written to disk and then read again by the safety scan — whose own purpose includes
resisting oversized documents.

None of this contradicts ADR 0004. That decision declines to guard the operator against their own
mistakes. This one guards the process against what a third party sends it, which is the other side
of the same boundary.

## Revisit if

A requirement appears for a scheme beyond `http`/`https` — an authenticated transport, or fetching
from a local file URL for symmetry with the path argument. Adding one is adding a handler, and the
threat model above has to be re-read against it rather than the handler simply appended.
