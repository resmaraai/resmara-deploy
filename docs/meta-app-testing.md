# Testing Resmara against the real Facebook app

App: **Resmara**, ID `1135911812356864`, owned by Be Authentic Productions. Production sends its
OAuth to this app (`META_CLIENT_ID` on the Render service — a client id that does not match the
secret on the same service fails every exchange with "Error validating client secret").

This is the checklist for testing the real login, Page, Instagram and ad-account flow before (and
after) App Review. It is written for two people: Dan, who has developer access to the app, and
whoever is testing from an agent session.

## 1. Who is allowed to log in at all

An app's **mode** decides it, and nothing else does:

| Mode | Who can grant permissions |
|---|---|
| Development | only people with a **role** on the app (Administrator, Developer, Tester, Authorized App Tester) |
| Live | anyone — but only for permissions **approved** in App Review; role users still get every permission the app can ask for |

So while the three App Review permissions (`pages_read_user_content`, `instagram_manage_comments`,
`email`) are pending, a normal agent's Facebook login can succeed and still be missing them. A
role user's login gets them. Test with a role account, or accept that the dialog will not show
them to a stranger until review clears.

**Adding people** — App Dashboard → **App Roles** → *Add People to This App*:

- **Administrator** — full control, including app secret and roles. Dan only.
- **Developer** — all technical settings and all permissions in development. Adam's `resmaraai`
  Meta developer account belongs here.
- **Tester** — all permissions in development, no settings. The right role for a coach or agent
  who is helping test.
- **Authorized App Tester** — a plain Facebook account with no Meta developer account. It accepts
  an invite in *Facebook → Settings & privacy → Your activity → Apps and Websites → Requests*.
  This is the 2026 path for "someone who is not a developer but must log in".

Meta is currently limiting **Test Users** (the synthetic accounts under App Roles). If that panel
refuses to create one, use a real Facebook account as a Tester or Authorized App Tester instead —
the test is more realistic anyway.

Limits: 50 testers on an unverified app; 500 administrators.

## 2. What the tester's Facebook account must own

Permissions are only half of it. For Connect Meta to return something useful, the account doing
the login needs:

- **A Facebook Page** it has full control of (the Page chooser lists the Pages the login manages).
- **An Instagram business or creator account** linked to that Page, if posts are going to
  Instagram.
- **An ad account it can see**, with a payment method on it. An ad account with no card creates
  campaigns that sit PAUSED forever and looks like a bug in Resmara; the token-health check now
  says so in Meta's own words instead.

An ad account that lives in a Business Manager has to be assigned to the tester in Business
Settings → Accounts → Ad accounts, or `/api/oauth/meta/callback` will find zero accounts and
answer `no_accounts`.

## 3. One-time settings on the app (Dan, in the dashboard)

App Dashboard → **Facebook Login for Business → Settings**:

- **Valid OAuth Redirect URIs** must contain exactly `https://www.resmara.com/api/oauth/meta/callback`
  for the production app. A redirect URI that is not listed word-for-word is refused before the
  consent screen ever appears.
- **App domains** must include `resmara.com`.
- Client OAuth login and Web OAuth login on; "Enforce HTTPS" on.

App Dashboard → **App settings → Basic**: the app ID, secret, privacy policy URL and data
deletion instructions must be filled in — App Review rejects an app with those blank.

The scopes the login asks for come from `META_SCOPES` **on the Render service**, not from
`render.yaml` (that file is the inventory, not the live value). Reading the live list is one call:

```sh
curl -s -H "Authorization: Bearer $(cat ~/.hermes/profiles/dev/secrets/render-api-key)" \
  "https://api.render.com/v1/services/srv-dbml2aei0phs73c6639g/env-vars?limit=50" | \
  python3 -c "import sys,json;[print(e['envVar']['key'],'=',e['envVar'].get('value')) for e in json.load(sys.stdin) if e['envVar']['key'] in ('META_SCOPES','META_CLIENT_ID','MAIL_FROM')]"
```

## 4. The test itself, in order

1. Open `https://www.resmara.com` in a **clean browser profile** (not the one an agent drives —
   a CDP-attached Chromium is refused at a Facebook sign-in).
2. Sign in, then Accounts → **Connect Meta**. The consent dialog must name all fourteen
   permissions; `pages_read_user_content`, `instagram_manage_comments` and `email` are the three
   App Review cares about. Screenshot this — it is the shot the review video needs.
3. Approve. Landing back with `?meta=several_pages` must say *"Meta connected — this login manages
   N Pages"* and open **Which Page is your business?** with no red bar. Pick the Page.
4. Accounts must show the ad account, the Page and the Instagram handle, and **Check connection**
   must come back healthy rather than "needs reconnecting".
5. Build one campaign and stop at the approval step: the point is to prove the flow, not to spend
   money. A launch against an account with no payment method must be refused with Meta's own
   reason, not attempted.

## 5. Proving it from the agent side, without a browser

```sh
# What the app is serving, and whether migrations applied
curl -s https://www.resmara.com/api/version

# Every check, including the Meta logins row (token status + expiry)
curl -s -H "X-Resmara-Token: $(cat the publish token)" https://www.resmara.com/api/admin/system-check

# The exact consent URL the site builds, including its scope list, without logging in:
# mint an HS256 token with the service's SECRET_KEY and sub = a real users.email, then
curl -s -H "Authorization: Bearer <jwt>" https://www.resmara.com/api/oauth/meta/connect
```

The last one is the honest proof that the dialog will ask for a permission: the returned
`redirect_url` carries `scope=` as Meta will receive it. Use a test account's email, and clear the
token from any browser it was put into.

## 6. What App Review actually wants to see

One recording per permission, showing the user granting it **and** the feature using it:

- `pages_read_user_content` — the Page's own posts read into the campaign/report.
- `instagram_manage_comments` — a comment on our own post read, and a reply posted from Resmara.
- `email` — the consent screen itself showing the email permission (it is a login permission, and
  the review video only has to show it being asked for and granted).

The submitter is Adam; the app stays in whichever mode it is in until review clears. Do not switch
the app to Live mid-review to "make testing easier" — it changes what the recording shows.
