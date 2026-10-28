# covers.com diagnostic

_Run because `source_health` reported covers tickets and handle at 0/1 while the board showed no plays. The parsers fail soft, so an outage leaves no stack trace — this is what the site actually returned._

## Consensus (tickets + handle)

`https://contests.covers.com/consensus/topconsensus/mlb/overall`

- HTTP **200** · 306,484 bytes · content-type `text/html; charset=utf-8`
- final URL after redirects: `https://contests.covers.com/consensus/topconsensus/mlb/overall`
- title: `MLB Public Betting, Money Percentages & Splits`
- `__NEXT_DATA__` present: **False**
- tables: **0** · rows: **0**

- class names containing 'overs'/'onsensus' (**101**): `Covers-CoversFooter`, `Covers-CoversFooter--bottom`, `Covers-CoversFooter-legal`, `Covers-CoversFooter-top`, `Covers-CoversFooterV2-logo`, `Covers-CoversFooterV2-verifiedSafe`, `cmg_consensus_dropdown`, `consensus-caret`, `consensusFilterSelect`, `consensusLeagueSelect`, `consensusSidesSelect`, `covers`, `covers-Container`, `covers-Container-aside`, `covers-Container-main`, `covers-CoversConsensus-consensusNav`, `covers-CoversConsensus-definitionBrick`, `covers-CoversConsensus-faqQ`, `covers-CoversConsensus-header`, `covers-CoversConsensus-i`, `covers-CoversConsensus-introText`, `covers-CoversDesktop-arrowRight`, `covers-CoversDesktop-sporticon`, `covers-CoversFooter-desktopSocial`, `covers-CoversFooter-gambleAware`

<details><summary>first 40 class names on the page</summary>

```
Covers-CoversFooter, Covers-CoversFooter--bottom, Covers-CoversFooter-legal, Covers-CoversFooter-top, Covers-CoversFooterV2-logo, Covers-CoversFooterV2-verifiedSafe, app-banner, app-banner-container, app-banner-headline, app-banner-left, app-banner-right, app-banner-store-logo, baseball-icon, basketball-icon, betting, bettingTitle, border-radius-4px, casinoTitle, close, cmg_communityLeaders_spinner, cmg_consensus_dropdown, cmg_date_picker--new, cmg_gambleaware_ca, cmg_gambleaware_int, cmg_gambleaware_us, cmg_geocontent_ca, cmg_geocontent_us, cmg_geocontent_zz, col, col-md-10, col-md-2, col-md-3, col-md-4, col-md-8, col-sm-5, col-xs-12, col-xs-6, collapse, collapsed, consensus-caret
```
</details>

<details><summary>where did the data go?</summary>

- candidate data URLs (**76**):

    - `/consensus/faq`
    - `/consensus/pickleaders`
    - `/consensus/pickleadersbyleagueteam`
    - `/consensus/publicmoney`
    - `/consensus/topconsensus/all/overall`
    - `/consensus/topconsensus/cfl/overall`
    - `/consensus/topconsensus/mlb/expert`
    - `/consensus/topconsensus/mlb/overall`
    - `/consensus/topconsensus/mlb/top10pct`
    - `/consensus/topconsensus/nba/overall`
    - `/consensus/topconsensus/ncaaf/overall`
    - `/consensus/topconsensus/nfl/overall`
    - `/consensus/topconsensus/nhl/overall`
    - `/consensus/topconsensus/wnba/overall`
    - `/consensus/topconsensusaway/mlb/overall`
    - `/consensus/topconsensushome/mlb/overall`
    - `/consensus/topoverunderconsensus/mlb/overall`
    - `https://apps.apple.com/us/app/covers-scores-picks-and-odds/id6749450176`
    - `https://contests.covers.com/consensus`
    - `https://contests.covers.com/consensus/faq`
    - `https://contests.covers.com/consensus/pickleaders/all?orderPickBy=Overall&amp;orderBy=Units`
    - `https://contests.covers.com/consensus/pickleadersbyleagueteam`
    - `https://contests.covers.com/consensus/publicmoney`
    - `https://contests.covers.com/consensus/topconsensus/all`
    - `https://contests.covers.com/consensus/topconsensus/cfl/overall`

- scripts mentioning consensus/percent/tickets (**1**):

    - `(anonymous)` (1,751 chars): `$(".covers-CoversConsensus-i").click(function (e) {             e.stopPropagation();             $(".covers-CoversConsensus-definitionBrick").slideToggle(); `

- `NN%` in RAW html: **110** (includes CSS widths — not evidence on its own)
- `NN%` in VISIBLE text, script/style stripped: **5** (first few: 10, 59, 59, 58, 62)
- `pickleadersbyteam` team anchors: **0** — the team anchors are gone too
- visible text length: **18,948** chars

    visible text around each `NN%`:

    ```
    … ers are making with consensus picks All Leagues NCAAF NFL MLB NBA NHL WNBA CFL Overall Team Money Leaders Top 10% Sides Totals Home Over 59% Away Over 59% No other matchups available. For baseball fans and experienced betto …
    … us picks All Leagues NCAAF NFL MLB NBA NHL WNBA CFL Overall Team Money Leaders Top 10% Sides Totals Home Over 59% Away Over 59% No other matchups available. For baseball fans and experienced bettors, understanding MLB publi …
    … eagues NCAAF NFL MLB NBA NHL WNBA CFL Overall Team Money Leaders Top 10% Sides Totals Home Over 59% Away Over 59% No other matchups available. For baseball fans and experienced bettors, understanding MLB public betting tren …
    … centage of MLB moneyline favorites win? Historically, MLB moneyline favorites have been observed to win about 58% to 62% of their games. Though this fluctuates seasonally, bettors should not bet solely on favorites as it ma …
    …  of MLB moneyline favorites win? Historically, MLB moneyline favorites have been observed to win about 58% to 62% of their games. Though this fluctuates seasonally, bettors should not bet solely on favorites as it may not b …
    ```

    HTML around the first one:

    ```html
    <div class="covers-CoversConsensus-consensusNav" style="display: none;">
    <div class="cmg_date_picker--new">
    <input class="text-box single-line" data-currentpage="/consensus/topconsensus/mlb/overall" id="CompetitionDate" name="SelectedDate" type="text" value=""/>
    </div>
    <div class="consensusLeagueSelect form-group">
    <span class="consensus-caret"></span>
    <select class="form-control cmg_consensus_dropdown" id="consensusLeagueDDL" name="consensusLeagueDDL"><option value="/consensus/topconsensus/all/overall">All Leagues</option>
    <option value="/consensus/topconsensus/ncaaf/overall">NCAAF</option>
    <option value="/consensus/topconsensus/nfl/overall">NFL</option>
    <option selected="selected" value="/
    ```
- distinct `data-*` attributes (**9**): `data-blockingmode`, `data-casino-target`, `data-cbid`, `data-cookieconsent`, `data-currentpage`, `data-dismiss`, `data-linkcont`, `data-target`, `data-toggle`

- elements whose whole text is `NN%`: **0**

</details>

## Odds / slate lines

`https://www.covers.com/sport/baseball/mlb/odds`

- HTTP **200** · 793,376 bytes · content-type `text/html; charset=utf-8`
- final URL after redirects: `https://www.covers.com/sport/baseball/mlb/odds`
- title: `MLB Odds 2026 - Best Online & Vegas Baseball Odds & Lines`
- `__NEXT_DATA__` present: **False**
- tables: **5** · rows: **20**

- class names containing 'overs'/'onsensus' (**116**): `Covers-CoversFooter`, `Covers-CoversFooter--bottom`, `Covers-CoversFooter-legal`, `Covers-CoversFooter-top`, `Covers-CoversFooterV2-logo`, `Covers-CoversFooterV2-verifiedSafe`, `covers`, `covers-Article-LH-Container`, `covers-Container`, `covers-Covers-OddsRelated-Article-Grid-Cont`, `covers-Covers-PageIntroCopy`, `covers-Covers-SportsbookPromos-Article-Grid-Cont`, `covers-CoversDesktop-arrowRight`, `covers-CoversDesktop-sporticon`, `covers-CoversFooter-desktopSocial`, `covers-CoversFooter-gambleAware`, `covers-CoversFooter-gambleAwareComp`, `covers-CoversFooter-linksBlock`, `covers-CoversFooter-mainLinks`, `covers-CoversFooter-promoBlock`, `covers-CoversFooter-promoCont`, `covers-CoversFooter-promoLeft`, `covers-CoversFooter-promoRight`, `covers-CoversFooter-socialLink`, `covers-CoversFooter-topLinkCont`

<details><summary>first 40 class names on the page</summary>

```
American, Covers-CoversFooter, Covers-CoversFooter--bottom, Covers-CoversFooter-legal, Covers-CoversFooter-top, Covers-CoversFooterV2-logo, Covers-CoversFooterV2-verifiedSafe, Decimal, Fraction, LH-LeagueDatetime-box, LH-datetime, LH-h2-Headlines, LH-league, LH-readMore, LH-title, Odds__DropdownCont, __OddsInfo, __SettingOdds, __actionGroup-btn, __american, __bet, __cancelActio-btn, __conference, __confirmedAction-btn, __content, __decimal, __dropdown, __filters, __fractional, __gameType, __infoIcon, __leagues, __li, __mb16px, __nextLevel, __nextMenu, __oddsScope, __oddsSetting, __title, __tooltipCont
```
</details>

<details><summary>where did the data go?</summary>

- candidate data URLs (**124**):

    - `/odds`
    - `/sport/MatchupOdds/OddsPage`
    - `/sport/baseball/mlb/matchup/395574`
    - `/sport/baseball/mlb/matchup/395578`
    - `/sport/baseball/mlb/matchup/395579`
    - `/sport/baseball/mlb/odds`
    - `/sport/baseball/mlb/odds/futures`
    - `/sport/basketball/nba/odds`
    - `/sport/basketball/ncaab/odds`
    - `/sport/basketball/wnba/odds`
    - `/sport/football/cfl/odds`
    - `/sport/football/ncaaf/odds`
    - `/sport/football/nfl/odds`
    - `/sport/golf/pga/odds`
    - `/sport/hockey/nhl/odds`
    - `/sport/soccer/champions-league/odds`
    - `/sport/soccer/mls/odds`
    - `/sport/soccer/premier-league/odds`
    - `/sports/mlb/matchups`
    - `https://apps.apple.com/us/app/covers-scores-picks-and-odds/id6749450176`
    - `https://contests.covers.com/consensus/faq`
    - `https://contests.covers.com/consensus/pickleaders/all?orderPickBy=Overall&amp;orderBy=Units`
    - `https://contests.covers.com/consensus/pickleadersbyleagueteam`
    - `https://contests.covers.com/consensus/publicmoney`
    - `https://contests.covers.com/consensus/topconsensus/all`

- scripts mentioning consensus/percent/tickets (**1**):

    - `mobileConfTabContent` (6,625 chars): `var mobileConfTabContent = "";     var selectedConf = "";      document.addEventListener('DOMContentLoaded', function() {         var OddsFilters = OddsPage`

- `NN%` in RAW html: **119** (includes CSS widths — not evidence on its own)
- `NN%` in VISIBLE text, script/style stripped: **0** — **the percentages are genuinely NOT being delivered**
- `pickleadersbyteam` team anchors: **0** — the team anchors are gone too
- visible text length: **27,991** chars
- distinct `data-*` attributes (**29**): `data-action`, `data-area`, `data-away-conference`, `data-away-team-rank`, `data-betslip-legs`, `data-betslip-source`, `data-blockingmode`, `data-book`, `data-casino-target`, `data-cbid`, `data-controller`, `data-cookieconsent`, `data-date`, `data-dismiss`, `data-enable-betslip`, `data-fallback-url`, `data-game`, `data-home-conference`, `data-home-team-rank`, `data-is-deeplink`

- elements whose whole text is `NN%`: **0**

</details>

## Forum listing

`https://www.covers.com/forum/mlb-betting-27`

- HTTP **200** · 1,082,963 bytes · content-type `text/html; charset=utf-8`
- final URL after redirects: `https://www.covers.com/forum/mlb-betting-27`
- title: `MLB Betting Forum | Covers`
- `__NEXT_DATA__` present: **False**
- tables: **0** · rows: **0**
- ⚠️ page text contains **'captcha'** — looks like a block, not a markup change

- class names containing 'overs'/'onsensus' (**68**): `covers`, `covers-Container`, `covers-Container-main`, `covers-CoversFeedback-submit`, `covers-CoversFooter-gambleAware`, `covers-CoversFooter-gambleAwareComp`, `covers-CoversFooter-promoCont`, `covers-CoversFooter-promoRight`, `covers-CoversFooterV2-communityCTA`, `covers-CoversForm-SearchButton`, `covers-CoversForm-viewThreadsTH`, `covers-CoversForum-DesktopPagerBottom`, `covers-CoversForum-breadcrumbLabel`, `covers-CoversForum-breadcrumbs`, `covers-CoversForum-createContainer`, `covers-CoversForum-createdTimestamp`, `covers-CoversForum-h3`, `covers-CoversForum-hotTopics`, `covers-CoversForum-hotTopicsList`, `covers-CoversForum-hotTopicsTitle`, `covers-CoversForum-lastPostLink`, `covers-CoversForum-lastPostLink2`, `covers-CoversForum-lastPostMobile`, `covers-CoversForum-linkBtn`, `covers-CoversForum-linkBtn--clear`

<details><summary>first 40 class names on the page</summary>

```
Icon, active, align-items-center, align-items-md-start, animate-fade, app-banner, app-banner-container, app-banner-headline, app-banner-left, app-banner-right, app-banner-store-logo, banner-skeleton, bg-white, border-0, bottom-text, bottom-wrapper, box-shadow, btn, btn-default, btn-group, btn-group-toggle, btn-loggedIn, btn-primary, btn-secondary, btn-sm, close, cmg_gambleaware_us, cmg_geocontent_us, col, col-12, col-6, col-lg-1, col-lg-2, col-lg-3, col-lg-5, col-md-1, col-md-3, col-md-4, col-sm-1, col-sm-2
```
</details>

<details><summary>where did the data go?</summary>

- candidate data URLs (**60**):

    - `/api/growthbook/attributes`
    - `https://apps.apple.com/us/app/covers-scores-picks-and-odds/id6749450176`
    - `https://contests.covers.com/consensus/faq`
    - `https://contests.covers.com/consensus/pickleaders/all?orderPickBy=Overall&amp;orderBy=Units`
    - `https://contests.covers.com/consensus/pickleadersbyleagueteam`
    - `https://contests.covers.com/consensus/publicmoney`
    - `https://contests.covers.com/consensus/topconsensus/all`
    - `https://contests.covers.com/consensus/topconsensus/cfl/overall`
    - `https://contests.covers.com/consensus/topconsensus/mlb/overall`
    - `https://contests.covers.com/consensus/topconsensus/nba/overall`
    - `https://contests.covers.com/consensus/topconsensus/ncaab/overall`
    - `https://contests.covers.com/consensus/topconsensus/ncaaf/overall`
    - `https://contests.covers.com/consensus/topconsensus/nfl/overall`
    - `https://contests.covers.com/consensus/topconsensus/nhl/overall`
    - `https://contests.covers.com/consensus/topconsensus/wnba/overall`
    - `https://data.covers.com`
    - `https://data.covers.com/cff7fdda0680/launch-490b3d016bbf.min.js`
    - `https://www.covers.com/golf/british-open/odds`
    - `https://www.covers.com/golf/masters/odds`
    - `https://www.covers.com/golf/pga-championship/odds`
    - `https://www.covers.com/golf/ryder-cup/odds`
    - `https://www.covers.com/golf/us-open/odds`
    - `https://www.covers.com/headers/build/js/covers/odds-shark-popup.min.js`
    - `https://www.covers.com/nfl/panthers-vs-packers-prediction-picks-odds-early-leans-week-8-2026`
    - `https://www.covers.com/nfl/week-8-odds-opening-lines-2026`

- scripts mentioning consensus/percent/tickets (**0**):

    - none

- `NN%` in RAW html: **272** (includes CSS widths — not evidence on its own)
- `NN%` in VISIBLE text, script/style stripped: **0** — **the percentages are genuinely NOT being delivered**
- `pickleadersbyteam` team anchors: **0** — the team anchors are gone too
- visible text length: **19,299** chars
- distinct `data-*` attributes (**24**): `data-aatracker`, `data-ad-attribute`, `data-backdrop`, `data-blockingmode`, `data-bs-target`, `data-bs-toggle`, `data-cbid`, `data-cookieconsent`, `data-currentpage`, `data-dismiss`, `data-entry-id`, `data-forum-id`, `data-hasmore`, `data-linkcont`, `data-mini`, `data-page-number`, `data-parent-target`, `data-role`, `data-target`, `data-thread-id`

- elements whose whole text is `NN%`: **0**

</details>

## What the CURRENT parser gets

- `consensus()` returned **0** teams
- `slate_lines()` returned **1** games

## Reading it

- a non-200, or a captcha/Cloudflare marker, means access is blocked and no selector change fixes it
- 200 with **no `covers-*` class names** means the markup was rebuilt and the selectors need repinning
- 200 with `__NEXT_DATA__` present means the numbers are rendered client-side and should be read from that JSON, not the DOM
