# License philosophy

> **Every feature documented in this repository stays in OSS forever
> under AGPL-3.0. New features may launch hosted-only and migrate to
> OSS later — but never the reverse.**

This is the contract. It doesn't change.

## What that means in practice

- Every feature in [README.md](README.md), the spec, and the docs is
  in OSS today and will remain in OSS in every future version.
- If we ever launch a hosted version, hosted-only features may exist
  there *first*. They migrate **into** OSS over time, never the other
  way.
- We will not remove features from OSS to "encourage" hosted upgrades.
- If our priorities change and a hosted version doesn't make sense, OSS
  continues. There is no scenario in which OSS gets worse to make
  hosted look better.

## What about license changes?

The Contributor License Agreement (CLA) grants Crowditory Ltd the
right to re-license future versions (e.g. AGPL → BSL). If we ever do
so, **all prior AGPL releases remain AGPL**. The community keeps
forever what it has at the moment of the change.

## Why we picked AGPL

Stops AWS, Google, Microsoft, etc. from running Geshtu as a competing
hosted service without contributing changes back. It does **not**
restrict:

- Internal use inside a company
- Forking and modifying for your own deployments
- Building tooling, plugins, or extensions on top
- Academic, journalistic, or educational use

It only requires that *if you offer Geshtu as a service to third
parties*, you publish your modifications. That's the bargain.

## Commercial license

For users whose use cases are incompatible with AGPL (typically large
enterprises proxying Geshtu through closed-source products), a
commercial license is available. Contact <licensing@geshtu.io>.

The commercial license **does not** unlock features. It simply lifts
the AGPL obligations. Same code.
