# Changelog

## 0.6.2 - 2025-10-08

- doc(readme): add version and download badges
- feat(link): link command no longer add link URLs in note body

## 0.6.1 - 2025-10-06

- chore(script): minor update on release script
- refactor(cli): move delete and prune into services
- feat(cli): add short flags and help alias
- feat(cli): rename export flag to format

## 0.6.0 - 2025-10-04

- feat(info): surface tags summary
- feat(cli): add prune subcommand

## 0.5.1 - 2025-10-01

- fix(storage): clear tag relations before deleting notes
- fix(storage): harden transactional updates and tag filters

## 0.5.0 - 2025-09-28

- feat(cli): allow setting created timestamp on log and link
## 0.4.1 - 2025-09-27

- fix(editor): refresh last edited and expose extra data (e.g. links)
- feat(datetime): show timestamps in local timezone

## 0.4.0 - 2025-09-27

- feat(cli): introduce `tn link` command to save URLs with Wayback fallback integration
- feat(export): switch to yaml front matter and jinja templates

## 0.3.0 - 2025-09-26

- chore(scripts): add a script to prepare a release + just target
- feat(export): add html and markdown exporters
