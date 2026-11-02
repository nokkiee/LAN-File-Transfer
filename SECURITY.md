# Security Policy

## Supported versions

Only the latest release gets security fixes. Apps from 1.1.0 onward can be
updated over Wi‑Fi. Older copies need to be replaced by hand with the latest
version from the [Releases page](https://github.com/nokkiee/LAN-File-Transfer/releases/latest).

| Version | Supported |
|---------|-----------|
| latest 1.1.x release | ✅ |
| 1.0.x and older | ❌ (replace it with the latest version) |

## Reporting a vulnerability

**Please don't report security problems in a public issue.** Report them
privately on the **Security** tab → **Report a vulnerability**
([direct link](https://github.com/nokkiee/LAN-File-Transfer/security/advisories/new)).
Only the maintainer can see these reports.

Please include:

- what the problem is and what an attacker could do with it
- the steps to reproduce it, or a proof of concept
- the app version and the operating systems involved

This is a personal project, so there's no guaranteed response time. Reports are
taken seriously, though. Once a fix is released, the issue will be published as
a security advisory, crediting you if you'd like.

## What the app protects against

- **Writing outside the receive folder:** file names from the other computer
  are untrusted. Absolute paths and `..` are refused, and names that aren't
  valid on Windows are fixed, before anything is written.
- **Unwanted files:** nothing is saved until you click **Accept**, unless you
  turn *Ask before accepting incoming files* off in Settings.
- **Fake or tampered updates:** an update is only installed if it's signed with
  the maintainer's private Ed25519 key, newer than the installed version, built
  for that system and matches the checksum in the signed manifest. It also has
  to start successfully once before it replaces the current app.

Ways around any of these are exactly what we want to hear about.

## Known limitations (by design)

The app is meant for a trusted home network. These are documented trade-offs,
not vulnerabilities:

- **Transfers aren't encrypted.** Someone else on the same network who can see
  or alter the traffic could read the files or change them on the way. Each
  file's checksum catches accidental damage, but not deliberate changes.
  App updates are different: they're signed, so changing one is detected.
- **Your computer is visible on the network.** The app announces its name,
  operating system, IP address and app version to the local network so other
  copies can find it.
- **Anyone on the network can send you an offer.** You still decide whether to
  accept it, unless you've turned the question off.

Reports that could make these safer without making the app harder to use are
welcome too.
