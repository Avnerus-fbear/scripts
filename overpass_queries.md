# Overpass queries behind the Hämeenlinna trip plan

Cottage coordinates used: **60.9207, 24.4446** (N 60° 55.240 / E 24° 26.674).

## How to run them

**Method A — one-line URL (easiest).** Paste into the address bar; the query is in the `data=` parameter and it must be URL-encoded (`[`→`%5B`, `]`→`%5D`, `"`→`%22`, `;`→`%3B`, spaces are fine):

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=<encoded query>
```

**Method B — the friendly editor.** Open <https://overpass-turbo.eu>, paste the raw query, hit Run. You can then view results as a map, a table, or GeoJSON. This is the better tool for actually *exploring* rather than spot-checking.

**Method C — curl** (what I used):

```bash
curl -s --data-urlencode 'data=<query>' \
     https://maps.mail.ru/osm/tools/overpass/api/interpreter
```

> **Endpoint that works for me (and is worth bookmarking):**
> `https://maps.mail.ru/osm/tools/overpass/api/interpreter`
> It's an Overpass mirror I found after the main endpoint kept refusing my requests. Note it is **flaky in a
> specific way: it intermittently returns `504 Gateway Time-out` on the first attempt and succeeds on the second**,
> so if you see a 504 just hit reload — that's a cold-worker symptom, not a broken query. The main public
> endpoint (`overpass-api.de`) returned `406 Not Acceptable` / `502` for most of my requests from this network.
> Both are rate-limited shared services, so expect to retry regardless of which you use.

## The queries

### 1. Which river is at the cottage? (rivers/streams within 1.2 km, named roads within 600 m)

```overpassql
[out:json][timeout:25];(way(around:1200,60.9207,24.4446)["waterway"~"river|stream"]["name"];way(around:600,60.9207,24.4446)["highway"]["name"];);out center;
```

<details><summary>URL-encoded (click, then copy)</summary>

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=%5Bout:json%5D%5Btimeout:25%5D;(way(around:1200,60.9207,24.4446)%5B%22waterway%22~%22river%7Cstream%22%5D%5B%22name%22%5D;way(around:600,60.9207,24.4446)%5B%22highway%22%5D%5B%22name%22%5D;);out%20center;
```
</details>

### 2. Rapids / waterfalls within 1.5 km

```overpassql
[out:json][timeout:25];node(around:1500,60.9207,24.4446)["natural"="waterfall"];out;
```

<details><summary>URL-encoded (click, then copy)</summary>

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=%5Bout:json%5D%5Btimeout:25%5D;node(around:1500,60.9207,24.4446)%5B%22natural%22=%22waterfall%22%5D;out;
```
</details>

### 3. Every bikeable track/path within 2.5 km (surface matters)

```overpassql
[out:json][timeout:35];way(around:2500,60.9207,24.4446)["highway"~"^(path|track)$"];out tags center;
```

<details><summary>URL-encoded (click, then copy)</summary>

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=%5Bout:json%5D%5Btimeout:35%5D;way(around:2500,60.9207,24.4446)%5B%22highway%22~%22%5E(path%7Ctrack)$%22%5D;out%20tags%20center;
```
</details>

### 4. What surface are they? (counts by surface tag, JSON dump of 1 km window)

```overpassql
[out:json][timeout:35];way(around:1000,60.9207,24.4446)["highway"~"^(path|track|unclassified)$"];out tags;
```

<details><summary>URL-encoded (click, then copy)</summary>

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=%5Bout:json%5D%5Btimeout:35%5D;way(around:1000,60.9207,24.4446)%5B%22highway%22~%22%5E(path%7Ctrack%7Cunclassified)$%22%5D;out%20tags;
```
</details>

### 5. Forest routes / hiking areas within 8 km

```overpassql
[out:json][timeout:25];(node(around:8000,60.9207,24.4446)["tourism"="viewpoint"];way(around:8000,60.9207,24.4446)["leisure"~"nature_reserve|park"]["name"];);out center;
```

<details><summary>URL-encoded (click, then copy)</summary>

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=%5Bout:json%5D%5Btimeout:25%5D;(node(around:8000,60.9207,24.4446)%5B%22tourism%22=%22viewpoint%22%5D;way(around:8000,60.9207,24.4446)%5B%22leisure%22~%22nature_reserve%7Cpark%22%5D%5B%22name%22%5D;);out%20center;
```
</details>

### 6. Everything tagged tourism within 10 km (playgrounds, information boards, museums)

```overpassql
[out:json][timeout:25];node(around:10000,60.9207,24.4446)["tourism"];out center;
```

<details><summary>URL-encoded (click, then copy)</summary>

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=%5Bout:json%5D%5Btimeout:25%5D;node(around:10000,60.9207,24.4446)%5B%22tourism%22%5D;out%20center;
```
</details>

### 7. Restaurants in Hämeenlinna town centre (around the castle)

```overpassql
[out:json][timeout:25];node(around:1500,60.9971,24.4620)["amenity"="restaurant"];out;
```

<details><summary>URL-encoded (click, then copy)</summary>

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=%5Bout:json%5D%5Btimeout:25%5D;node(around:1500,60.9971,24.4620)%5B%22amenity%22=%22restaurant%22%5D;out;
```
</details>

### 8. Churches near the castle (for the Orthodox-church visit)

```overpassql
[out:json][timeout:25];(node(around:1200,60.9971,24.4620)["amenity"="place_of_worship"];way(around:1200,60.9971,24.4620)["amenity"="place_of_worship"];);out center;
```

<details><summary>URL-encoded (click, then copy)</summary>

```
https://maps.mail.ru/osm/tools/overpass/api/interpreter?data=%5Bout:json%5D%5Btimeout:25%5D;(node(around:1200,60.9971,24.4620)%5B%22amenity%22=%22place_of_worship%22%5D;way(around:1200,60.9971,24.4620)%5B%22amenity%22=%22place_of_worship%22%5D;);out%20center;
```
</details>

## Handy tag cheatsheet for reading the results

| Tag | What it means for you |
|---|---|
| `highway=track` + `tracktype=grade1/2` | Firm gravel/dirt forest road — bikeable with kids |
| `highway=track` + `tracktype=grade4/5` | Soft sand / grass / muddy — push the bike |
| `surface=mud` or `surface=dirt` | Avoid in October unless you like carrying a 4-year-old |
| no `surface` tag at all | Nobody mapped it. Go and look, or ask the host |
| `highway=path` + `mtb:scale=*` | Mountain-bike difficulty scale (1 easiest → 6) |
| `natural=waterfall` / `waterway=river` | The water your cottage is named for |
| `leisure=nature_reserve` | Protected area — stay on existing paths |
| `tourism=viewpoint` | Scenic platform (e.g. Aulangon näkötorni) |
