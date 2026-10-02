# Initial connection reliability

This is a bounded reliability follow-up to the adopted consumer-entry journey, not a new activation or product feature. Source inspection of main `9f0aeb5f031da663337bf606052d1a2fc384dd4b` found that the outer `/v1/development/status` read has no deadline or in-flight ownership while its always-enabled retry button can stack requests. This outer route must resolve before ordinary member entry can appear.

The first draft adds two provider-free browser regressions against injected status responses: a held initial request must end after 15 seconds, settle the actual fetch, show an explicit retry and recover to member entry; a pending read must be visible and cannot stack duplicate reads. Hosted reproduction is pending. No real credentials, accounts, provider, trial window or database configuration are involved.

Local browser execution is unavailable in the restored execution container because Chromium cannot create its singleton socket; no local browser pass is claimed. Normal exact-head CI remains the acceptance path. The separate PR28 exact-main materialization transport failure is being retried independently and is not a product-test failure.
