# U2-01 consumer journey acceptance

Implementation and verification in progress. Browser evidence must cover mobile login, connection recovery, bounded sign-in without automatic repeat, first-message inline consent and unavailable-generation draft preservation. Existing account isolation, owner/guest regressions and the complete broad browser suite remain required.

The prior exact-main account screenshots established two concrete UX gaps: the mobile entry used unstyled controls unlike the adopted chat, and first send required visiting Settings. Source review also found an unbounded login/register request and no manual recovery after an initial account-status outage. This slice addresses those paths without changing server authority.

No live Auth settings, account, entitlement, key, model call or guest window is activated by these changes. The live consumer service is not ready until its separately blocked configuration and delivery are established.
