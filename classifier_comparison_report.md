# SpinSleeve Classifier Comparison & Confidence Report (Regex vs. Semantic)

**Generated for User ID:** `sergebou` | **GCP Project:** `secret-compass-181513`

---

📁 **Total Saved Library Albums Analyzed:** 1906


## 1. Aggregated Macro-Genre Distribution Comparison

```markdown
                      Regex (Legacy Count)  Regex %  Semantic (Zero-Shot Count)  Semantic %
Ambient                                195     10.2                          97         5.1
Blues                                    1      0.1                           5         0.3
Classical                               51      2.7                          61         3.2
Electronic                             173      9.1                         115         6.0
Folk / Country                         133      7.0                          75         3.9
Hip-Hop                                 25      1.3                          33         1.7
Jazz                                   147      7.7                         210        11.0
Latin / World                           20      1.0                          32         1.7
Metal                                    0      0.0                           2         0.1
Other / Unclassified                   646     33.9                         553        29.0
Pop                                    208     10.9                         317        16.6
Punk / Alternative                      84      4.4                          71         3.7
R&B / Soul                              47      2.5                          56         2.9
Reggae / Dub                             4      0.2                          18         0.9
Rock                                   172      9.0                         261        13.7
```


## 2. Semantic Confidence & Threshold Analysis
Breakdown of semantic similarity confidence scores (cosine distance against macro-genre anchors):
- **High Confidence ($\ge 0.50$):** 971 albums (50.9%)
- **Moderate Confidence ($0.40 - 0.49$):** 199 albums (10.4%)
- **Borderline Confidence ($0.35 - 0.39$):** 103 albums (5.4%)
- **Fallback Triggered ($< 0.35$):** 633 albums (33.2%)


## 3. Divergence & Discrepancy Highlights
Total divergences detected between Regex and Semantic: **418** out of 1906 albums.

| Album Name                                                                                 | Artist                     | Genres Corpus                                                                                                          | Regex                    | Semantic               | Confidence |
| :----------------------------------------------------------------------------------------- | :------------------------- | :--------------------------------------------------------------------------------------------------------------------- | :----------------------- | :--------------------- | :--------: |
| Automated Improvisation                                                                    | Move 78                    | `nu jazz, indie jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |   `0.73`   |
| Suite                                                                                      | GODTET                     | `ambient jazz, experimental jazz`                                                                                      | **Ambient**              | **Jazz**               |  `0.659`   |
| Little Sigh                                                                                | Marika Hackman             | `southern gothic, ambient folk`                                                                                        | **Ambient**              | **Folk / Country**     |  `0.492`   |
| Reflection (I – IV)                                                                        | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Tape 2                                                                                     | Felbm                      | `ambient jazz`                                                                                                         | **Ambient**              | **Jazz**               |  `0.647`   |
| Peach                                                                                      | Alabaster DePlume          | `ambient jazz`                                                                                                         | **Ambient**              | **Jazz**               |  `0.647`   |
| Palms                                                                                      | Robohands                  | `indie jazz, nu jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |  `0.728`   |
| Sleep Games                                                                                | Pye Corner Audio           | `idm, space rock, ambient`                                                                                             | **Ambient**              | **Electronic**         |  `0.618`   |
| The Alias Sessions                                                                         | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Glancing Backwards: The Dawn Anthology                                                     | John Surman                | `free jazz, ambient jazz, jazz`                                                                                        | **Ambient**              | **Jazz**               |  `0.755`   |
| Flight Instructions                                                                        | Move 78                    | `nu jazz, indie jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |   `0.73`   |
| La sangre iluminada                                                                        | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Surbahar Sleeping Music                                                                    | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Oranj                                                                                      | Robohands                  | `indie jazz, nu jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |  `0.728`   |
| Copernicus - The Good Book of No                                                           | Alabaster DePlume          | `ambient jazz`                                                                                                         | **Ambient**              | **Jazz**               |  `0.647`   |
| Resavoir                                                                                   | Resavoir                   | `experimental jazz, ambient jazz, jazz house`                                                                          | **Ambient**              | **Jazz**               |  `0.695`   |
| It's Always About Love                                                                     | Ancient Infinity Orchestra | `ambient jazz`                                                                                                         | **Ambient**              | **Jazz**               |  `0.647`   |
| The Etna Sessions                                                                          | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| The Versailles Sessions                                                                    | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Point Blank                                                                                | Tony Kofi                  | `ambient jazz`                                                                                                         | **Ambient**              | **Jazz**               |  `0.647`   |
| Music for Peace and Harmony                                                                | Hiro Ama                   | `ambient jazz`                                                                                                         | **Ambient**              | **Jazz**               |  `0.647`   |
| EP02                                                                                       | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Music for Saxofone & Bass Guitar                                                           | Sam Gendel                 | `ambient jazz, experimental jazz, nu jazz, indie jazz`                                                                 | **Ambient**              | **Jazz**               |   `0.73`   |
| While The Flood Rages                                                                      | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Dusk                                                                                       | Robohands                  | `indie jazz, nu jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |  `0.728`   |
| Lost in Time                                                                               | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Symphonie Pacifique                                                                        | Greg Foat                  | `ambient jazz, nu jazz, experimental jazz`                                                                             | **Ambient**              | **Jazz**               |  `0.697`   |
| Slime                                                                                      | Marika Hackman             | `southern gothic, ambient folk`                                                                                        | **Ambient**              | **Folk / Country**     |  `0.492`   |
| Shapes                                                                                     | Robohands                  | `indie jazz, nu jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |  `0.728`   |
| Lumen                                                                                      | Bill Laurance              | `jazz fusion, jazz, nu jazz, ambient jazz`                                                                             | **Ambient**              | **Jazz**               |  `0.767`   |
| EP03                                                                                       | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Eno (Original Motion Picture Soundtrack)                                                   | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| From Sleep                                                                                 | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Twin Color, Vol. 1                                                                         | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Quiet Logic                                                                                | Mixmaster Morris           | `idm, ambient`                                                                                                         | **Ambient**              | **Electronic**         |  `0.563`   |
| EP01                                                                                       | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Tremors in the Static                                                                      | Vega Trails                | `ambient jazz`                                                                                                         | **Ambient**              | **Jazz**               |  `0.647`   |
| Violet                                                                                     | Robohands                  | `indie jazz, nu jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |  `0.728`   |
| Three Worlds: Music From Woolf Works                                                       | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Earth Patterns                                                                             | Szun Waves                 | `ambient jazz, nu jazz, experimental jazz, indie jazz`                                                                 | **Ambient**              | **Jazz**               |  `0.732`   |
| Seeing Through Sound (Pentimento Volume Two)                                               | Jon Hassell                | `ambient jazz, ambient, minimalism, experimental jazz, electroacoustic, drone, musique concrète, avant-garde`          | **Ambient**              | **Jazz**               |   `0.73`   |
| Brian Eno - Film Music 1976 ~ 2020                                                         | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| In The Age Of Data                                                                         | Move 78                    | `nu jazz, indie jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |   `0.73`   |
| Ill Considered III                                                                         | Ill Considered             | `nu jazz, free jazz, experimental jazz, ambient jazz, jazz, indie jazz, jazz fusion`                                   | **Ambient**              | **Jazz**               |  `0.808`   |
| The Algorithm Smiles Upon You                                                              | Move 78                    | `nu jazz, indie jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |   `0.73`   |
| WILKES                                                                                     | Sam Wilkes                 | `ambient jazz, nu jazz, experimental jazz, indie jazz`                                                                 | **Ambient**              | **Jazz**               |  `0.732`   |
| Game Four                                                                                  | Move 78                    | `nu jazz, indie jazz, ambient jazz`                                                                                    | **Ambient**              | **Jazz**               |   `0.73`   |
| Top Boy (Score from the Original Series)                                                   | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| The Jewel In The Lotus                                                                     | Bennie Maupin              | `free jazz, ambient jazz, jazz fusion, jazz funk, experimental jazz`                                                   | **Ambient**              | **Jazz**               |   `0.81`   |
| Pharoah                                                                                    | Pharoah Sanders            | `free jazz, ambient jazz, jazz, experimental jazz, hard bop`                                                           | **Ambient**              | **Jazz**               |  `0.776`   |
| Different Trains / Electric Counterpoint                                                   | Steve Reich                | `minimalism, contemporary classical, avant-garde, musique concrète, electroacoustic, classical, experimental, ambient` | **Ambient**              | **Classical**          |  `0.599`   |
| Ambient 4: On Land (Remastered 2004)                                                       | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Ptah The El Daoud                                                                          | Alice Coltrane             | `free jazz, jazz, experimental jazz, ambient jazz`                                                                     | **Ambient**              | **Jazz**               |  `0.782`   |
| Soundscapes Vol. 1 - Music for Harlequins                                                  | Gianni Brezzo              | `nu jazz, ambient jazz, indie jazz, jazz funk`                                                                         | **Ambient**              | **Jazz**               |  `0.727`   |
| Le plan de Paris                                                                           | Pascal Comelade            | `musique concrète`                                                                                                     | **Other / Unclassified** | **Jazz**               |  `0.354`   |
| Statea                                                                                     | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Robyn                                                                                      | cktrl                      | `ambient jazz`                                                                                                         | **Ambient**              | **Jazz**               |  `0.647`   |
| Recomposed By Max Richter: Vivaldi, The Four Seasons                                       | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Cascade                                                                                    | Floating Points            | `idm, ambient jazz, gnawa`                                                                                             | **Ambient**              | **Electronic**         |  `0.632`   |
| Toward The Within (Remastered)                                                             | Dead Can Dance             | `neofolk, darkwave, gothic rock, deathrock, neoclassical, post-punk, new age, cold wave`                               | **Ambient**              | **Punk / Alternative** |  `0.711`   |
| Mighty Vertebrate                                                                          | Anna Butterss              | `ambient jazz, indie jazz, experimental jazz`                                                                          | **Ambient**              | **Jazz**               |  `0.709`   |
| Wrong Way Up [Expanded Edition]                                                            | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Music Has The Right To Children                                                            | Boards of Canada           | `idm, ambient, trip hop, downtempo, electronic`                                                                        | **Ambient**              | **Electronic**         |  `0.677`   |
| Crush                                                                                      | Floating Points            | `idm, ambient jazz, gnawa`                                                                                             | **Ambient**              | **Electronic**         |  `0.632`   |
| The Blue Notebooks (15 Years)                                                              | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Quique Redux (2025 Remaster)                                                               | Seefeel                    | `idm, shoegaze, post-rock, ambient, drone`                                                                             | **Ambient**              | **Electronic**         |  `0.625`   |
| Sam Wilkes, Craig Weinrib, and Dylan Day                                                   | Sam Wilkes                 | `ambient jazz, nu jazz, experimental jazz, indie jazz`                                                                 | **Ambient**              | **Jazz**               |  `0.732`   |
| Sleep                                                                                      | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Late Night Tales: Jon Hopkins                                                              | Jon Hopkins                | `idm, ambient`                                                                                                         | **Ambient**              | **Electronic**         |  `0.563`   |
| Shall We Go On Sinning So That Grace May Increase?                                         | The Soft Pink Truth        | `ambient, idm`                                                                                                         | **Ambient**              | **Electronic**         |  `0.556`   |
| Space 1.8                                                                                  | Nala Sinephro              | `ambient jazz, ambient, experimental jazz, nu jazz`                                                                    | **Ambient**              | **Jazz**               |  `0.708`   |
| Any Human Friend                                                                           | Marika Hackman             | `southern gothic, ambient folk`                                                                                        | **Ambient**              | **Folk / Country**     |  `0.492`   |
| Ambient 1: Music For Airports (Remastered 2004)                                            | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Singularity                                                                                | Jon Hopkins                | `idm, ambient`                                                                                                         | **Ambient**              | **Electronic**         |  `0.563`   |
| Cheetah EP                                                                                 | Aphex Twin                 | `idm, ambient`                                                                                                         | **Ambient**              | **Electronic**         |  `0.563`   |
| Apollo                                                                                     | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| AZD                                                                                        | Actress                    | `idm, ambient, experimental`                                                                                           | **Ambient**              | **Electronic**         |  `0.532`   |
| Endlessness                                                                                | Nala Sinephro              | `ambient jazz, ambient, experimental jazz, nu jazz`                                                                    | **Ambient**              | **Jazz**               |  `0.708`   |
| Drukqs                                                                                     | Aphex Twin                 | `idm, ambient`                                                                                                         | **Ambient**              | **Electronic**         |  `0.563`   |
| Liminal                                                                                    | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Promises                                                                                   | Floating Points            | `idm, ambient jazz, gnawa`                                                                                             | **Ambient**              | **Electronic**         |  `0.632`   |
| Atlas                                                                                      | Laurel Halo                | `art pop, ambient, drone, experimental, electroacoustic, idm`                                                          | **Ambient**              | **Electronic**         |  `0.702`   |
| Suite for Max Brown                                                                        | Jeff Parker                | `ambient jazz, experimental jazz, free jazz, nu jazz`                                                                  | **Ambient**              | **Jazz**               |   `0.76`   |
| Karma & Desire                                                                             | Actress                    | `idm, ambient, experimental`                                                                                           | **Ambient**              | **Electronic**         |  `0.532`   |
| Sol.Hz                                                                                     | Seefeel                    | `idm, shoegaze, post-rock, ambient, drone`                                                                             | **Ambient**              | **Electronic**         |  `0.625`   |
| Twin Color (Extended Play No. 2)                                                           | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| Cosmos                                                                                     | Murcof                     | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical`                                         | **Ambient**              | **Electronic**         |  `0.701`   |
| The Ship                                                                                   | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| The New Four Seasons - Vivaldi Recomposed                                                  | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Small Craft                                                                                | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Salute to the Sun                                                                          | Matthew Halsall            | `ambient jazz, jazz, nu jazz, indie jazz`                                                                              | **Ambient**              | **Jazz**               |  `0.735`   |
| choke enough                                                                               | Oklou                      | `art pop, hyperpop`                                                                                                    | **Electronic**           | **Pop**                |  `0.474`   |
| Quarantine                                                                                 | Laurel Halo                | `art pop, ambient, drone, experimental, electroacoustic, idm`                                                          | **Ambient**              | **Electronic**         |  `0.702`   |
| Contre-Temps                                                                               | Flavien Berger             | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Eternity                                                                                   | Alice Coltrane             | `free jazz, jazz, experimental jazz, ambient jazz`                                                                     | **Ambient**              | **Jazz**               |  `0.782`   |
| Small Craft On A Milk Sea                                                                  | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Discreet Music                                                                             | Brian Eno                  | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music`                                              | **Ambient**              | **Rock**               |  `0.718`   |
| Songs From Before                                                                          | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Sleep Circle                                                                               | Max Richter                | `neoclassical, contemporary classical, minimalism, ambient, classical`                                                 | **Ambient**              | **Classical**          |  `0.484`   |
| Raw Silk Uncut Wood                                                                        | Laurel Halo                | `art pop, ambient, drone, experimental, electroacoustic, idm`                                                          | **Ambient**              | **Electronic**         |  `0.702`   |
| Zuckerzeit                                                                                 | Cluster                    | `krautrock, ambient, space rock, drone, avant-garde`                                                                   | **Ambient**              | **Rock**               |  `0.648`   |
| Utopia                                                                                     | Björk                      | `art pop, trip hop`                                                                                                    | **Electronic**           | **Hip-Hop**            |  `0.561`   |
| Inferno                                                                                    | Boards of Canada           | `idm, ambient, trip hop, downtempo, electronic`                                                                        | **Ambient**              | **Electronic**         |  `0.677`   |
| Fourth World Vol 1 Possible Musics                                                         | Jon Hassell                | `ambient jazz, ambient, minimalism, experimental jazz, electroacoustic, drone, musique concrète, avant-garde`          | **Ambient**              | **Jazz**               |   `0.73`   |
| Disraeli Gears                                                                             | Cream                      | `classic rock, psychedelic rock, acid rock, blues rock`                                                                | **Blues**                | **Rock**               |  `0.715`   |
| Lazaretto                                                                                  | Jack White                 | `blues rock, garage rock`                                                                                              | **Electronic**           | **Blues**              |  `0.553`   |
| Mule Variations (Remastered)                                                               | Tom Waits                  | `singer-songwriter, southern gothic`                                                                                   | **Folk / Country**       | **R&B / Soul**         |   `0.42`   |
| Fear Of The Dawn                                                                           | Jack White                 | `blues rock, garage rock`                                                                                              | **Electronic**           | **Blues**              |  `0.553`   |
| No Name                                                                                    | Jack White                 | `blues rock, garage rock`                                                                                              | **Electronic**           | **Blues**              |  `0.553`   |
| Entering Heaven Alive                                                                      | Jack White                 | `blues rock, garage rock`                                                                                              | **Electronic**           | **Blues**              |  `0.553`   |
| Interior Live Oak                                                                          | Cass McCombs               | `baroque pop, singer-songwriter`                                                                                       | **Folk / Country**       | **Pop**                |  `0.537`   |
| Sticky Wickets                                                                             | The Duckworth Lewis Method | `baroque pop, comedy`                                                                                                  | **Pop**                  | **Classical**          |  `0.517`   |
| Gavin Bryards : Allegrasco - Alaric I or II - Three Elegics                                | Gavin Bryars               | `minimalism, contemporary classical, avant-garde, electroacoustic`                                                     | **Classical**            | **Ambient**            |  `0.485`   |
| Métode De Rocanrol                                                                         | Pascal Comelade            | `musique concrète`                                                                                                     | **Other / Unclassified** | **Jazz**               |  `0.354`   |
| Seed Cake On Leap Year                                                                     | Cass McCombs               | `baroque pop, singer-songwriter`                                                                                       | **Folk / Country**       | **Pop**                |  `0.537`   |
| Demoed                                                                                     | Lambchop                   | `alt country, baroque pop, americana`                                                                                  | **Folk / Country**       | **Pop**                |  `0.563`   |
| After The Requiem                                                                          | Gavin Bryars               | `minimalism, contemporary classical, avant-garde, electroacoustic`                                                     | **Classical**            | **Ambient**            |  `0.485`   |
| Prefection                                                                                 | Cass McCombs               | `baroque pop, singer-songwriter`                                                                                       | **Folk / Country**       | **Pop**                |  `0.537`   |
| Wainwright: Dream Requiem                                                                  | Rufus Wainwright           | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| Veckatimest                                                                                | Grizzly Bear               | `indie, baroque pop, indie rock`                                                                                       | **Rock**                 | **Pop**                |  `0.756`   |
| Flotus                                                                                     | Lambchop                   | `alt country, baroque pop, americana`                                                                                  | **Folk / Country**       | **Pop**                |  `0.563`   |
| Heartmind                                                                                  | Cass McCombs               | `baroque pop, singer-songwriter`                                                                                       | **Folk / Country**       | **Pop**                |  `0.537`   |
| The Bible                                                                                  | Lambchop                   | `alt country, baroque pop, americana`                                                                                  | **Folk / Country**       | **Pop**                |  `0.563`   |
| My Finest Work Yet                                                                         | Andrew Bird                | `baroque pop, indie folk`                                                                                              | **Folk / Country**       | **Pop**                |  `0.658`   |
| Mangy Love                                                                                 | Cass McCombs               | `baroque pop, singer-songwriter`                                                                                       | **Folk / Country**       | **Pop**                |  `0.537`   |
| Wit's End                                                                                  | Cass McCombs               | `baroque pop, singer-songwriter`                                                                                       | **Folk / Country**       | **Pop**                |  `0.537`   |
| Damaged                                                                                    | Lambchop                   | `alt country, baroque pop, americana`                                                                                  | **Folk / Country**       | **Pop**                |  `0.563`   |
| What A Terrible World, What A Beautiful World                                              | The Decemberists           | `baroque pop, indie folk`                                                                                              | **Folk / Country**       | **Pop**                |  `0.658`   |
| HARK!                                                                                      | Andrew Bird                | `baroque pop, indie folk`                                                                                              | **Folk / Country**       | **Pop**                |  `0.658`   |
| Painted Ruins                                                                              | Grizzly Bear               | `indie, baroque pop, indie rock`                                                                                       | **Rock**                 | **Pop**                |  `0.756`   |
| Showtunes                                                                                  | Lambchop                   | `alt country, baroque pop, americana`                                                                                  | **Folk / Country**       | **Pop**                |  `0.563`   |
| Further                                                                                    | Richard Hawley             | `baroque pop, singer-songwriter`                                                                                       | **Folk / Country**       | **Pop**                |  `0.537`   |
| Closure                                                                                    | Piano Magic                | `post-rock, baroque pop, slowcore, dream pop`                                                                          | **Rock**                 | **Pop**                |  `0.683`   |
| No Other                                                                                   | Gene Clark                 | `country rock, baroque pop, folk rock, americana`                                                                      | **Folk / Country**       | **Rock**               |  `0.661`   |
| Tip of the Sphere                                                                          | Cass McCombs               | `baroque pop, singer-songwriter`                                                                                       | **Folk / Country**       | **Pop**                |  `0.537`   |
| This (Is What I Wanted to Tell You)                                                        | Lambchop                   | `alt country, baroque pop, americana`                                                                                  | **Folk / Country**       | **Pop**                |  `0.563`   |
| Hug Of Thunder                                                                             | Broken Social Scene        | `baroque pop, indie rock, indie`                                                                                       | **Rock**                 | **Pop**                |  `0.741`   |
| Filmmusik Anthology 6                                                                      | Irmin Schmidt              | `krautrock, avant-garde`                                                                                               | **Other / Unclassified** | **Rock**               |  `0.491`   |
| Countdown: 1992-1983                                                                       | Pulp                       | `britpop`                                                                                                              | **Other / Unclassified** | **Pop**                |  `0.359`   |
| Archives                                                                                   | Vanishing Twin             | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Villa wunderbar                                                                            | Irmin Schmidt              | `krautrock, avant-garde`                                                                                               | **Other / Unclassified** | **Rock**               |  `0.491`   |
| Texas Sun                                                                                  | Khruangbin                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Ookii Gekkou                                                                               | Vanishing Twin             | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Orange Wine                                                                                | Okvsho                     | `jazz house, nu jazz, indie jazz`                                                                                      | **Electronic**           | **Jazz**               |  `0.688`   |
| Suppose                                                                                    | Blue House                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Frozen Flashes                                                                             | Okvsho                     | `jazz house, nu jazz, indie jazz`                                                                                      | **Electronic**           | **Jazz**               |  `0.688`   |
| The Age Of Immunology                                                                      | Vanishing Twin             | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Phonetics On and On                                                                        | Horsegirl                  | `lo-fi indie`                                                                                                          | **Other / Unclassified** | **Pop**                |  `0.532`   |
| Gobstopper                                                                                 | Blue House                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Nothing's Changed                                                                          | Justus Proffit             | `lo-fi indie`                                                                                                          | **Other / Unclassified** | **Pop**                |  `0.532`   |
| In Piscina!                                                                                | Vanishing Twin             | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Waterslide, Diving Board, Ladder To The Sky                                                | Porridge Radio             | `lo-fi indie`                                                                                                          | **Other / Unclassified** | **Pop**                |  `0.532`   |
| Late Night Tales: Metronomy (Sampler)                                                      | Metronomy                  | `new rave, alternative dance`                                                                                          | **Other / Unclassified** | **Reggae / Dub**       |  `0.406`   |
| Paralelo                                                                                   | Pascal Comelade            | `musique concrète`                                                                                                     | **Other / Unclassified** | **Jazz**               |  `0.354`   |
| Texas Moon                                                                                 | Khruangbin                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Some Other Ones                                                                            | Mac DeMarco                | `indie, lo-fi indie`                                                                                                   | **Other / Unclassified** | **Pop**                |  `0.622`   |
| Petunia                                                                                    | Tonstartssbandht           | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Daybreak                                                                                   | Sven Wunder                | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Anthology Soundtrack 1,2 & 3                                                               | Irmin Schmidt              | `krautrock, avant-garde`                                                                                               | **Other / Unclassified** | **Rock**               |  `0.491`   |
| Carré noir sur fond noir                                                                   | Pascal Comelade            | `musique concrète`                                                                                                     | **Other / Unclassified** | **Jazz**               |  `0.354`   |
| With You Every Night                                                                       | Ariel Pink                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Filmmusik Anthology 4 & 5                                                                  | Irmin Schmidt              | `krautrock, avant-garde`                                                                                               | **Other / Unclassified** | **Rock**               |  `0.491`   |
| Pelota                                                                                     | Khruangbin                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Living Thing                                                                               | Peter Bjorn and John       | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Dita Von Teese                                                                             | Dita Von Teese             | `italo disco`                                                                                                          | **Other / Unclassified** | **Latin / World**      |  `0.381`   |
| Late Night Tales: Khruangbin                                                               | Khruangbin                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| The Versatile Henry Mancini And His Orchestra                                              | Henry Mancini              | `exotica, adult standards, easy listening`                                                                             | **Other / Unclassified** | **Latin / World**      |  `0.486`   |
| El Baile Alemán                                                                            | Señor Coconut              | `cha cha cha, exotica`                                                                                                 | **Other / Unclassified** | **Latin / World**      |  `0.351`   |
| Reset Mariachi EP                                                                          | Panda Bear                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Darker Days                                                                                | Peter Bjorn and John       | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Hovvdy                                                                                     | Hovvdy                     | `lo-fi indie`                                                                                                          | **Other / Unclassified** | **Pop**                |  `0.532`   |
| Blossoms                                                                                   | Blossoms                   | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Weird Little Birthday                                                                      | Happyness                  | `lo-fi indie`                                                                                                          | **Other / Unclassified** | **Pop**                |  `0.532`   |
| PAINT                                                                                      | PAINT                      | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| April                                                                                      | Sun Kil Moon               | `slowcore, southern gothic`                                                                                            | **Other / Unclassified** | **Metal**              |  `0.423`   |
| Mordechai                                                                                  | Khruangbin                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Lush                                                                                       | Snail Mail                 | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Nation Shall Speak Unto Nation                                                             | Edwyn Collins              | `britpop`                                                                                                              | **Other / Unclassified** | **Pop**                |  `0.359`   |
| Ti Amo                                                                                     | Phoenix                    | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| A LA SALA                                                                                  | Khruangbin                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Tracey Denim                                                                               | bar italia                 | `lo-fi indie`                                                                                                          | **Other / Unclassified** | **Pop**                |  `0.532`   |
| The Slow Rush                                                                              | Tame Impala                | `neo-psychedelic, indie`                                                                                               | **Other / Unclassified** | **Rock**               |  `0.597`   |
| I've Been Trying To Tell You                                                               | Saint Etienne              | `madchester, britpop, alternative dance`                                                                               | **Other / Unclassified** | **Pop**                |  `0.451`   |
| Here Comes The Cowboy                                                                      | Mac DeMarco                | `indie, lo-fi indie`                                                                                                   | **Other / Unclassified** | **Pop**                |  `0.622`   |
| Hot Dreams                                                                                 | Timber Timbre              | `southern gothic`                                                                                                      | **Other / Unclassified** | **Latin / World**      |  `0.371`   |
| Autofiction                                                                                | Suede                      | `britpop, madchester`                                                                                                  | **Other / Unclassified** | **Pop**                |  `0.362`   |
| Guitar                                                                                     | Mac DeMarco                | `indie, lo-fi indie`                                                                                                   | **Other / Unclassified** | **Pop**                |  `0.622`   |
| One Wayne G                                                                                | Mac DeMarco                | `indie, lo-fi indie`                                                                                                   | **Other / Unclassified** | **Pop**                |  `0.622`   |
| We Will Always Love You                                                                    | The Avalanches             | `plunderphonics`                                                                                                       | **Other / Unclassified** | **Reggae / Dub**       |  `0.389`   |
| color theory                                                                               | Soccer Mommy               | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Eucalyptus                                                                                 | Avey Tare                  | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| More                                                                                       | Pulp                       | `britpop`                                                                                                              | **Other / Unclassified** | **Pop**                |  `0.359`   |
| American Head                                                                              | The Flaming Lips           | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Five Easy Hot Dogs                                                                         | Mac DeMarco                | `indie, lo-fi indie`                                                                                                   | **Other / Unclassified** | **Pop**                |  `0.622`   |
| american dream                                                                             | LCD Soundsystem            | `alternative dance, new rave`                                                                                          | **Other / Unclassified** | **Reggae / Dub**       |  `0.423`   |
| Wildflower                                                                                 | The Avalanches             | `plunderphonics`                                                                                                       | **Other / Unclassified** | **Reggae / Dub**       |  `0.389`   |
| Clean                                                                                      | Soccer Mommy               | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Reset (Expanded Edition)                                                                   | Panda Bear                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Ricochet                                                                                   | Snail Mail                 | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Metronomy Forever                                                                          | Metronomy                  | `new rave, alternative dance`                                                                                          | **Other / Unclassified** | **Reggae / Dub**       |  `0.406`   |
| V                                                                                          | Unknown Mortal Orchestra   | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Badbea                                                                                     | Edwyn Collins              | `britpop`                                                                                                              | **Other / Unclassified** | **Pop**                |  `0.359`   |
| Sincerely, Future Pollution                                                                | Timber Timbre              | `southern gothic`                                                                                                      | **Other / Unclassified** | **Latin / World**      |  `0.371`   |
| Cows on Hourglass Pond                                                                     | Avey Tare                  | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Panda Bear Meets The Grim Reaper                                                           | Panda Bear                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Afternoon X                                                                                | Vanishing Twin             | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Every Bad                                                                                  | Porridge Radio             | `lo-fi indie`                                                                                                          | **Other / Unclassified** | **Pop**                |  `0.532`   |
| Small World                                                                                | Metronomy                  | `new rave, alternative dance`                                                                                          | **Other / Unclassified** | **Reggae / Dub**       |  `0.406`   |
| The Smell of Our Own (20th Anniversary Edition)                                            | The Hidden Cameras         | `queercore`                                                                                                            | **Other / Unclassified** | **Punk / Alternative** |  `0.435`   |
| Con Todo El Mundo                                                                          | Khruangbin                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Gorgeous George                                                                            | Edwyn Collins              | `britpop`                                                                                                              | **Other / Unclassified** | **Pop**                |  `0.359`   |
| Summer 08                                                                                  | Metronomy                  | `new rave, alternative dance`                                                                                          | **Other / Unclassified** | **Reggae / Dub**       |  `0.406`   |
| Valentine                                                                                  | Snail Mail                 | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Buoys                                                                                      | Panda Bear                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| 2                                                                                          | Mac DeMarco                | `indie, lo-fi indie`                                                                                                   | **Other / Unclassified** | **Pop**                |  `0.622`   |
| Night Thoughts                                                                             | Suede                      | `britpop, madchester`                                                                                                  | **Other / Unclassified** | **Pop**                |  `0.362`   |
| Oczy Mlody                                                                                 | The Flaming Lips           | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Sinister Grift                                                                             | Panda Bear                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Goodbye Emmanuelle (Bande originale du film)                                               | Serge Gainsbourg           | `chanson, variété française, french pop, french jazz, french house`                                                    | **Electronic**           | **Jazz**               |  `0.454`   |
| Ciao Satan                                                                                 | Flavien Berger             | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Talent Stick                                                                               | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Education & Recreation                                                                     | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Recto Verso (Édition Augmentée)                                                            | Paradis                    | `french indie pop, french house, french pop`                                                                           | **Electronic**           | **Pop**                |  `0.544`   |
| plouf! (Léviathan)                                                                         | Flavien Berger             | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Palais d'argile                                                                            | Feu! Chatterton            | `french indie pop, french pop, french house, chanson, variété française`                                               | **Electronic**           | **Pop**                |  `0.544`   |
| Friendship Theme                                                                           | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Colón Man                                                                                  | Equiknoxx                  | `dancehall, soca, dub techno`                                                                                          | **Electronic**           | **Reggae / Dub**       |  `0.614`   |
| Breathe Deep                                                                               | Oscar Jerome               | `indie soul, jazz house, indie jazz, nu jazz`                                                                          | **Electronic**           | **Jazz**               |  `0.701`   |
| Superb                                                                                     | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Lightship 95 Sessions                                                                      | Oscar Jerome               | `indie soul, jazz house, indie jazz, nu jazz`                                                                          | **Electronic**           | **Jazz**               |  `0.701`   |
| Vivant                                                                                     | Malik Djoudi               | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Late Night Tales: Air (Sampler)                                                            | Air                        | `trip hop, downtempo`                                                                                                  | **Electronic**           | **Hip-Hop**            |  `0.369`   |
| Léviathan                                                                                  | Flavien Berger             | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Websites                                                                                   | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Vers les lueurs (Deluxe Edition)                                                           | Dominique A                | `french pop, chanson, variété française, french indie pop, french house`                                               | **Electronic**           | **Pop**                |  `0.504`   |
| Confessions                                                                                | Philippe Katerine          | `french pop, chanson, variété française, french indie pop, french house`                                               | **Electronic**           | **Pop**                |  `0.504`   |
| Toute latitude                                                                             | Dominique A                | `french pop, chanson, variété française, french indie pop, french house`                                               | **Electronic**           | **Pop**                |  `0.504`   |
| Wisdom and Lies                                                                            | Emperors New Clothes       | `acid jazz, trip hop`                                                                                                  | **Electronic**           | **Jazz**               |  `0.551`   |
| Labyrinthe                                                                                 | Feu! Chatterton            | `french indie pop, french pop, french house, chanson, variété française`                                               | **Electronic**           | **Pop**                |  `0.544`   |
| Suburban Breeze                                                                            | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Ouin Ouin                                                                                  | Miel De Montagne           | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Petite Amie                                                                                | Juliette Armanet           | `french pop, variété française, chanson, french house, french indie pop`                                               | **Electronic**           | **Pop**                |  `0.525`   |
| La Musique / La Matière (Edition Spéciale)                                                 | Dominique A                | `french pop, chanson, variété française, french indie pop, french house`                                               | **Electronic**           | **Pop**                |  `0.504`   |
| Spirales                                                                                   | Dominique A                | `french pop, chanson, variété française, french indie pop, french house`                                               | **Electronic**           | **Pop**                |  `0.504`   |
| Frogs In A Pond                                                                            | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Ouin Ouin Ouin                                                                             | Miel De Montagne           | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Iconoclasts                                                                                | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Tout Autour De Nous                                                                        | Miel De Montagne           | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| N°2                                                                                        | Serge Gainsbourg           | `chanson, variété française, french pop, french jazz, french house`                                                    | **Electronic**           | **Jazz**               |  `0.454`   |
| Tempéraments                                                                               | Malik Djoudi               | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| The Complete Golden Ravedays                                                               | Superpitcher               | `minimal techno`                                                                                                       | **Electronic**           | **Ambient**            |   `0.51`   |
| Study of the Invisible                                                                     | Vanessa Wagner             | `neoclassical, minimalism, electronic classical, contemporary classical`                                               | **Electronic**           | **Classical**          |  `0.399`   |
| Doubts and Convictions (Remastered)                                                        | Troublemakers              | `trip hop`                                                                                                             | **Electronic**           | **Hip-Hop**            |  `0.402`   |
| contrebande 02. le disque de l'été                                                         | Flavien Berger             | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Daylight Savings                                                                           | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| N°4                                                                                        | Serge Gainsbourg           | `chanson, variété française, french pop, french jazz, french house`                                                    | **Electronic**           | **Jazz**               |  `0.454`   |
| A place between us                                                                         | Okvsho                     | `jazz house, nu jazz, indie jazz`                                                                                      | **Electronic**           | **Jazz**               |  `0.688`   |
| Miel de Montagne                                                                           | Miel De Montagne           | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| Dans cent ans                                                                              | Flavien Berger             | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| All News Is Good News                                                                      | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Less Is Orchestra                                                                          | Alias                      | `experimental hip hop, underground hip hop, trip hop`                                                                  | **Electronic**           | **Hip-Hop**            |  `0.599`   |
| Le monde réel                                                                              | Dominique A                | `french pop, chanson, variété française, french indie pop, french house`                                               | **Electronic**           | **Pop**                |  `0.504`   |
| Twentyears                                                                                 | Air                        | `trip hop, downtempo`                                                                                                  | **Electronic**           | **Hip-Hop**            |  `0.369`   |
| Late Night Tales presents Sasha: Scene Delete                                              | Sasha                      | `trance, progressive house`                                                                                            | **Electronic**           | **Rock**               |  `0.407`   |
| Couleurs Primaires                                                                         | Paradis                    | `french indie pop, french house, french pop`                                                                           | **Electronic**           | **Pop**                |  `0.544`   |
| Trip Tease                                                                                 | Tipsy                      | `exotica, plunderphonics, trip hop`                                                                                    | **Electronic**           | **Reggae / Dub**       |  `0.453`   |
| Moon Safari Rarities (25th Anniversary Edition)                                            | Air                        | `trip hop, downtempo`                                                                                                  | **Electronic**           | **Hip-Hop**            |  `0.369`   |
| When Will We Land?                                                                         | Barry Can't Swim           | `jazz house`                                                                                                           | **Electronic**           | **Jazz**               |  `0.494`   |
| The Spoon                                                                                  | Oscar Jerome               | `indie soul, jazz house, indie jazz, nu jazz`                                                                          | **Electronic**           | **Jazz**               |  `0.701`   |
| Recto Verso                                                                                | Paradis                    | `french indie pop, french house, french pop`                                                                           | **Electronic**           | **Pop**                |  `0.544`   |
| The Spork                                                                                  | Oscar Jerome               | `indie soul, jazz house, indie jazz, nu jazz`                                                                          | **Electronic**           | **Jazz**               |  `0.701`   |
| YMO                                                                                        | YELLOW MAGIC ORCHESTRA     | `synthpop, city pop, kayōkyoku, shibuya-kei`                                                                           | **Electronic**           | **Pop**                |  `0.548`   |
| The Fork                                                                                   | Oscar Jerome               | `indie soul, jazz house, indie jazz, nu jazz`                                                                          | **Electronic**           | **Jazz**               |  `0.701`   |
| The Mountain Will Fall                                                                     | DJ Shadow                  | `trip hop, plunderphonics, downtempo`                                                                                  | **Electronic**           | **Hip-Hop**            |  `0.506`   |
| The Third Chimpanzee E.P.                                                                  | Martin Gore                | `synthpop`                                                                                                             | **Electronic**           | **Pop**                |   `0.56`   |
| Mystère                                                                                    | La Femme                   | `french indie pop, french pop, french house`                                                                           | **Electronic**           | **Pop**                |  `0.543`   |
| DJ-Kicks                                                                                   | Kruder & Dorfmeister       | `trip hop, downtempo, nu jazz, acid jazz`                                                                              | **Electronic**           | **Jazz**               |  `0.658`   |
| Happiness (Anniversary Edition)                                                            | Fridge                     | `post-rock, idm`                                                                                                       | **Electronic**           | **Rock**               |  `0.511`   |
| Season High                                                                                | Little Dragon              | `trip hop`                                                                                                             | **Electronic**           | **Hip-Hop**            |  `0.402`   |
| Strange Disciple                                                                           | Nation of Language         | `synthpop`                                                                                                             | **Electronic**           | **Pop**                |   `0.56`   |
| Late Night Tales: Barry Can't Swim (LNT Mix)                                               | Barry Can't Swim           | `jazz house`                                                                                                           | **Electronic**           | **Jazz**               |  `0.494`   |
| Money Music                                                                                | Surprise Chef              | `indie jazz, jazz funk, jazz house`                                                                                    | **Electronic**           | **Jazz**               |  `0.711`   |
| Fossora                                                                                    | Björk                      | `art pop, trip hop`                                                                                                    | **Electronic**           | **Hip-Hop**            |  `0.561`   |
| The Versions                                                                               | Rhythm & Sound             | `dub techno, dub, jazz house`                                                                                          | **Electronic**           | **Reggae / Dub**       |  `0.554`   |
| Late Night Tales: Music for Pleasure                                                       | Groove Armada              | `big beat, trip hop`                                                                                                   | **Electronic**           | **Hip-Hop**            |  `0.523`   |
| Late Night Tales: David Holmes                                                             | David Holmes               | `trip hop, big beat`                                                                                                   | **Electronic**           | **Hip-Hop**            |  `0.509`   |
| The Virgin Suicides Redux                                                                  | Air                        | `trip hop, downtempo`                                                                                                  | **Electronic**           | **Hip-Hop**            |  `0.369`   |
| Black Sands                                                                                | Bonobo                     | `trip hop, downtempo, nu jazz, electronic`                                                                             | **Electronic**           | **Jazz**               |  `0.601`   |
| Crèvecoeur (Super Deluxe Edition)                                                          | Daniel Darc                | `french pop, chanson, french house, variété française`                                                                 | **Electronic**           | **Pop**                |  `0.355`   |
| Migration                                                                                  | Bonobo                     | `trip hop, downtempo, nu jazz, electronic`                                                                             | **Electronic**           | **Jazz**               |  `0.601`   |
| No Bad Memories                                                                            | The Avalanches             | `plunderphonics`                                                                                                       | **Other / Unclassified** | **Reggae / Dub**       |  `0.389`   |
| Nabuma Rubberband                                                                          | Little Dragon              | `trip hop`                                                                                                             | **Electronic**           | **Hip-Hop**            |  `0.402`   |
| Reflektor                                                                                  | Arcade Fire                | `indie rock, baroque pop`                                                                                              | **Rock**                 | **Pop**                |  `0.691`   |
| Since I Left You                                                                           | The Avalanches             | `plunderphonics`                                                                                                       | **Other / Unclassified** | **Reggae / Dub**       |  `0.389`   |
| Congratulations                                                                            | MGMT                       | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| I´m Coming Home                                                                            | St. Thomas                 | `norsk rock, norwegian pop, anti-folk`                                                                                 | **Folk / Country**       | **Punk / Alternative** |  `0.436`   |
| Rise Above It: A Souled American Anthology                                                 | Souled American            | `alt country, slowcore, americana`                                                                                     | **Folk / Country**       | **Rock**               |  `0.461`   |
| Notes Campfire                                                                             | Souled American            | `alt country, slowcore, americana`                                                                                     | **Folk / Country**       | **Rock**               |  `0.461`   |
| You Ain't Big / Alone Time / Peaceful Afternoon / Damsel In Distress / Trouble In Paradise | Rufus Wainwright           | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| Big Bad Luv                                                                                | John Moreland              | `americana, alt country, red dirt`                                                                                     | **Folk / Country**       | **Blues**              |  `0.413`   |
| Rufus Wainwright (25th Anniversary Edition)                                                | Rufus Wainwright           | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| summerteeth (Deluxe Edition)                                                               | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Rufus Wainwright and Amsterdam Sinfonietta (Live)                                          | Rufus Wainwright           | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| Being There                                                                                | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Hey Mr Ferryman                                                                            | Mark Eitzel                | `slowcore, singer-songwriter, alt country`                                                                             | **Folk / Country**       | **Pop**                |  `0.496`   |
| Wanderer                                                                                   | Cat Power                  | `slowcore, singer-songwriter`                                                                                          | **Folk / Country**       | **R&B / Soul**         |  `0.416`   |
| Folkocracy                                                                                 | Rufus Wainwright           | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| Rain On Lens                                                                               | Smog                       | `slowcore, anti-folk, alt country`                                                                                     | **Folk / Country**       | **Rock**               |  `0.472`   |
| Ode to Joy                                                                                 | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Unfollow The Rules                                                                         | Rufus Wainwright           | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| Wilco (The Album)                                                                          | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| From A Basement On The Hill                                                                | Elliott Smith              | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| The Whole Love Expanded                                                                    | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| I Inside the Old Year Dying                                                                | PJ Harvey                  | `art pop, singer-songwriter, alternative rock`                                                                         | **Folk / Country**       | **Pop**                |   `0.65`   |
| A Ghost Is Born (Deluxe Version)                                                           | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Star Wars                                                                                  | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Schmilco                                                                                   | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Cousin                                                                                     | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Everybody Knows This Is Nowhere                                                            | Neil Young                 | `classic rock, folk rock, singer-songwriter, roots rock`                                                               | **Folk / Country**       | **Rock**               |  `0.632`   |
| You Want It Darker                                                                         | Leonard Cohen              | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| The Whole Love (Deluxe Edition)                                                            | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Sky Blue Sky                                                                               | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| Homegrown                                                                                  | Neil Young                 | `classic rock, folk rock, singer-songwriter, roots rock`                                                               | **Folk / Country**       | **Rock**               |  `0.632`   |
| Cruel Country                                                                              | Wilco                      | `alt country, americana, indie rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.627`   |
| A Crow Looked at Me                                                                        | Mount Eerie                | `slowcore, anti-folk, indie folk`                                                                                      | **Folk / Country**       | **Rock**               |  `0.607`   |
| Years to Burn                                                                              | Calexico                   | `alt country, americana, roots rock`                                                                                   | **Folk / Country**       | **Rock**               |  `0.546`   |
| a Mouse in a Crowded House                                                                 | St. Thomas                 | `norsk rock, norwegian pop, anti-folk`                                                                                 | **Folk / Country**       | **Punk / Alternative** |  `0.436`   |
| The Glow, Pt. 2                                                                            | The Microphones            | `slowcore, anti-folk, lo-fi indie, indie folk`                                                                         | **Folk / Country**       | **Rock**               |  `0.658`   |
| Colorado                                                                                   | Neil Young                 | `classic rock, folk rock, singer-songwriter, roots rock`                                                               | **Folk / Country**       | **Rock**               |  `0.632`   |
| Time Fades Away                                                                            | Neil Young                 | `classic rock, folk rock, singer-songwriter, roots rock`                                                               | **Folk / Country**       | **Rock**               |  `0.632`   |
| Frozen                                                                                     | Souled American            | `alt country, slowcore, americana`                                                                                     | **Folk / Country**       | **Rock**               |  `0.461`   |
| Elliott Smith                                                                              | Elliott Smith              | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| Release The Stars                                                                          | Rufus Wainwright           | `singer-songwriter`                                                                                                    | **Folk / Country**       | **R&B / Soul**         |  `0.441`   |
| Rain Dogs                                                                                  | Tom Waits                  | `singer-songwriter, southern gothic`                                                                                   | **Folk / Country**       | **R&B / Soul**         |   `0.42`   |
| The Hope Six Demolition Project                                                            | PJ Harvey                  | `art pop, singer-songwriter, alternative rock`                                                                         | **Folk / Country**       | **Pop**                |   `0.65`   |
| Bring Backs                                                                                | Alfa Mist                  | `nu jazz, jazz rap, indie jazz, jazz fusion, jazz`                                                                     | **Hip-Hop**              | **Jazz**               |  `0.757`   |
| Where I'm Meant To Be                                                                      | Ezra Collective            | `jazz rap, indie soul, nu jazz`                                                                                        | **Hip-Hop**              | **Jazz**               |  `0.687`   |
| DeBÍ TiRAR MáS FOToS                                                                       | Bad Bunny                  | `reggaeton, trap latino, latin, urbano latino`                                                                         | **Hip-Hop**              | **Latin / World**      |  `0.695`   |
| The Grind Date (20th Anniversary Edition)                                                  | De La Soul                 | `jazz rap, east coast hip hop`                                                                                         | **Hip-Hop**              | **Jazz**               |  `0.615`   |
| Athletic Progression                                                                       | Athletic Progression       | `nu jazz, jazz rap, indie jazz, experimental jazz`                                                                     | **Hip-Hop**              | **Jazz**               |  `0.746`   |
| A Night At Club Baobab (Senegalese Dance Music of the 70's)                                | Orchestra Baobab           | `afro-cuban jazz, afropop`                                                                                             | **Jazz**                 | **Latin / World**      |  `0.603`   |
| India                                                                                      | Gal Costa                  | `mpb, bossa nova, brazilian jazz`                                                                                      | **Jazz**                 | **Latin / World**      |  `0.615`   |
| Arthur Verocai                                                                             | Arthur Verocai             | `brazilian jazz, bossa nova, mpb`                                                                                      | **Jazz**                 | **Latin / World**      |  `0.605`   |
| Pirates Choice                                                                             | Orchestra Baobab           | `afro-cuban jazz, afropop`                                                                                             | **Jazz**                 | **Latin / World**      |  `0.603`   |
| Big Band Bossa Nova                                                                        | Quincy Jones               | `soul jazz, big band, quiet storm`                                                                                     | **Jazz**                 | **R&B / Soul**         |  `0.585`   |
| Getz/Gilberto #2                                                                           | Stan Getz                  | `bossa nova, jazz, brazilian jazz, cool jazz, latin jazz, jazz ballads`                                                | **Jazz**                 | **Latin / World**      |   `0.69`   |
| Gal Costa                                                                                  | Gal Costa                  | `mpb, bossa nova, brazilian jazz`                                                                                      | **Jazz**                 | **Latin / World**      |  `0.615`   |
| Clube Da Esquina                                                                           | Milton Nascimento          | `mpb, bossa nova, brazilian jazz`                                                                                      | **Jazz**                 | **Latin / World**      |  `0.615`   |
| Tribute to Ndiouga Dieng                                                                   | Orchestra Baobab           | `afro-cuban jazz, afropop`                                                                                             | **Jazz**                 | **Latin / World**      |  `0.603`   |
| We're New Here                                                                             | Gil Scott-Heron            | `spoken word, jazz funk`                                                                                               | **Jazz**                 | **R&B / Soul**         |  `0.518`   |
| Gula Matari                                                                                | Quincy Jones               | `soul jazz, big band, quiet storm`                                                                                     | **Jazz**                 | **R&B / Soul**         |  `0.585`   |
| The Stardust Road                                                                          | Hoagy Carmichael           | `big band, ragtime`                                                                                                    | **Jazz**                 | **Metal**              |  `0.384`   |
| The Dude                                                                                   | Quincy Jones               | `soul jazz, big band, quiet storm`                                                                                     | **Jazz**                 | **R&B / Soul**         |  `0.585`   |
| Pieces of a Man                                                                            | Gil Scott-Heron            | `spoken word, jazz funk`                                                                                               | **Jazz**                 | **R&B / Soul**         |  `0.518`   |
| Franks Wild Years                                                                          | Tom Waits                  | `singer-songwriter, southern gothic`                                                                                   | **Folk / Country**       | **R&B / Soul**         |   `0.42`   |
| The Ground                                                                                 | Tord Gustavsen Trio        | `jazz, ambient jazz`                                                                                                   | **Ambient**              | **Jazz**               |  `0.713`   |
| Stop The Hate                                                                              | Femi Kuti                  | `afrobeat, afropop, highlife`                                                                                          | **Latin / World**        | **R&B / Soul**         |  `0.617`   |
| Ka Rica-Tar                                                                                | Karl Hector & The Malcouns | `afrobeat, neo-psychedelic`                                                                                            | **Latin / World**        | **Rock**               |  `0.533`   |
| Arca                                                                                       | Arca                       | `neoperreo, experimental, art pop, hyperpop`                                                                           | **Electronic**           | **Pop**                |  `0.496`   |
| Birkin / Gainsbourg : Le symphonique                                                       | Jane Birkin                | `chanson, french pop, variété française`                                                                               | **Pop**                  | **Reggae / Dub**       |   `0.37`   |
| BRAT                                                                                       | Charli xcx                 | `hyperpop, art pop`                                                                                                    | **Electronic**           | **Pop**                |  `0.461`   |
| Soon Over Babluma (Remastered)                                                             | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| MiXology (volume 1)                                                                        | John Cale                  | `art rock, baroque pop, proto-punk, singer-songwriter`                                                                 | **Punk / Alternative**   | **Pop**                |  `0.677`   |
| LIVE IN ASTON 1977                                                                         | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| Sublime (10th Anniversary Edition / Deluxe Edition)                                        | Sublime                    | `reggae rock, ska punk, ska`                                                                                           | **Punk / Alternative**   | **Reggae / Dub**       |  `0.759`   |
| Future Days (Remastered)                                                                   | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| LIVE IN CUXHAVEN 1976                                                                      | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| Unlimited Edition (Remastered)                                                             | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| Tago Mago (40th Anniversary Edition)                                                       | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| Ege Bamyasi (Remastered)                                                                   | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| The Singles                                                                                | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| POPtical Illusion                                                                          | John Cale                  | `art rock, baroque pop, proto-punk, singer-songwriter`                                                                 | **Punk / Alternative**   | **Pop**                |  `0.677`   |
| Tin Drum                                                                                   | Japan                      | `new wave, synthpop, post-punk, art pop`                                                                               | **Punk / Alternative**   | **Pop**                |  `0.729`   |
| LIVE IN BRIGHTON 1975                                                                      | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| LIVE IN ARLES 1975                                                                         | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| Saw Delight (Remastered)                                                                   | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| LIVE IN PARIS 1973                                                                         | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| LIVE IN STUTTGART 1975                                                                     | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| Bedroom                                                                                    | bdrmm                      | `shoegaze, lo-fi indie, dream pop, post-punk`                                                                          | **Punk / Alternative**   | **Rock**               |  `0.728`   |
| The Lost Tapes                                                                             | CAN                        | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk`                        | **Punk / Alternative**   | **Rock**               |  `0.804`   |
| Small Things                                                                               | Nick Hakim                 | `indie soul`                                                                                                           | **R&B / Soul**           | **Rock**               |  `0.594`   |
| COMETA                                                                                     | Nick Hakim                 | `indie soul`                                                                                                           | **R&B / Soul**           | **Rock**               |  `0.594`   |
| Green Twins                                                                                | Nick Hakim                 | `indie soul`                                                                                                           | **R&B / Soul**           | **Rock**               |  `0.594`   |
| Where Will We Go, Pt. 2                                                                    | Nick Hakim                 | `indie soul`                                                                                                           | **R&B / Soul**           | **Rock**               |  `0.594`   |
| Where Will We Go, Pt. 1                                                                    | Nick Hakim                 | `indie soul`                                                                                                           | **R&B / Soul**           | **Rock**               |  `0.594`   |
| Lahai                                                                                      | Sampha                     | `indie soul`                                                                                                           | **R&B / Soul**           | **Rock**               |  `0.594`   |
| græ                                                                                        | Moses Sumney               | `art pop, indie soul`                                                                                                  | **R&B / Soul**           | **Pop**                |  `0.689`   |
| WILL THIS MAKE ME GOOD                                                                     | Nick Hakim                 | `indie soul`                                                                                                           | **R&B / Soul**           | **Rock**               |  `0.594`   |
| MAGDALENE                                                                                  | FKA twigs                  | `art pop, alternative r&b`                                                                                             | **R&B / Soul**           | **Pop**                |  `0.529`   |
| CAPRISONGS                                                                                 | FKA twigs                  | `art pop, alternative r&b`                                                                                             | **R&B / Soul**           | **Pop**                |  `0.529`   |
| Process                                                                                    | Sampha                     | `indie soul`                                                                                                           | **R&B / Soul**           | **Rock**               |  `0.594`   |
| Ecstatic Arrow                                                                             | Virginia Wing              | `space rock, art pop`                                                                                                  | **Rock**                 | **Pop**                |  `0.595`   |
| Serkut rakastaa paremmin                                                                   | Tv-Resistori               | `finnish rock, finnish pop`                                                                                            | **Rock**                 | **Pop**                |  `0.483`   |
| circle the drain                                                                           | Soccer Mommy               | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Snow Borne Sorrow                                                                          | Nine Horses                | `art rock, art pop`                                                                                                    | **Rock**                 | **Pop**                |  `0.642`   |
| Ash & Ice                                                                                  | The Kills                  | `garage rock`                                                                                                          | **Electronic**           | **Rock**               |  `0.488`   |
| Blue Rev                                                                                   | Alvvays                    | `dream pop, shoegaze, jangle pop, indie`                                                                               | **Rock**                 | **Pop**                |  `0.668`   |
| A Promise                                                                                  | Xiu Xiu                    | `art pop, noise rock`                                                                                                  | **Rock**                 | **Pop**                |  `0.636`   |
| In The Morse Code Of Brake Lights                                                          | The New Pornographers      | `power pop, indie rock, indie`                                                                                         | **Rock**                 | **Pop**                |  `0.735`   |
| Antisocialites                                                                             | Alvvays                    | `dream pop, shoegaze, jangle pop, indie`                                                                               | **Rock**                 | **Pop**                |  `0.668`   |
| Manafon                                                                                    | David Sylvian              | `art pop, art rock`                                                                                                    | **Rock**                 | **Pop**                |  `0.644`   |
| Plays the Music of Twin Peaks                                                              | Xiu Xiu                    | `art pop, noise rock`                                                                                                  | **Rock**                 | **Pop**                |  `0.636`   |
| Midnight Boom                                                                              | The Kills                  | `garage rock`                                                                                                          | **Electronic**           | **Rock**               |  `0.488`   |
| Whiteout Conditions                                                                        | The New Pornographers      | `power pop, indie rock, indie`                                                                                         | **Rock**                 | **Pop**                |  `0.735`   |
| The Car                                                                                    | Arctic Monkeys             | `indie, garage rock`                                                                                                   | **Electronic**           | **Rock**               |  `0.672`   |
| The Ballad of Darren                                                                       | Blur                       | `britpop, alternative rock`                                                                                            | **Rock**                 | **Punk / Alternative** |  `0.559`   |
| Mobile Home                                                                                | Longpigs                   | `britpop, madchester`                                                                                                  | **Other / Unclassified** | **Pop**                |  `0.362`   |
| Loss Of Life                                                                               | MGMT                       | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| This Old Dog                                                                               | Mac DeMarco                | `indie, lo-fi indie`                                                                                                   | **Other / Unclassified** | **Pop**                |  `0.622`   |
| Little Dark Age                                                                            | MGMT                       | `indie`                                                                                                                | **Other / Unclassified** | **Pop**                |  `0.591`   |
| Tranquility Base Hotel & Casino                                                            | Arctic Monkeys             | `indie, garage rock`                                                                                                   | **Electronic**           | **Rock**               |  `0.672`   |
| Think Tank                                                                                 | Blur                       | `britpop, alternative rock`                                                                                            | **Rock**                 | **Punk / Alternative** |  `0.559`   |
| Girl with Basket of Fruit                                                                  | Xiu Xiu                    | `art pop, noise rock`                                                                                                  | **Rock**                 | **Pop**                |  `0.636`   |
| Salad Days Demos                                                                           | Mac DeMarco                | `indie, lo-fi indie`                                                                                                   | **Other / Unclassified** | **Pop**                |  `0.622`   |
| Rare Birds                                                                                 | Jonathan Wilson            | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| Live at the Royal Albert Hall                                                              | Arctic Monkeys             | `indie, garage rock`                                                                                                   | **Electronic**           | **Rock**               |  `0.672`   |
| Dedicated to Bobby Jameson                                                                 | Ariel Pink                 | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |
| 7s                                                                                         | Avey Tare                  | `neo-psychedelic`                                                                                                      | **Other / Unclassified** | **Rock**               |  `0.408`   |

## 4. Full Catalog Classification Ledger
Complete itemized classification record with confidence scores for all 1906 albums:

| # | Album Name | Artist | Genres Corpus | Assigned Macro-Genre | Confidence |
| :---: | :--- | :--- | :--- | :--- | :---: |
| 1 | Kollektion 02: Roedelius (Electronic Music) | Roedelius | `krautrock, ambient, drone, minimalism` | **Ambient** | `0.636` |
| 2 | Automated Improvisation | Move 78 | `nu jazz, indie jazz, ambient jazz` | **Jazz** | `0.73` |
| 3 | Suite | GODTET | `ambient jazz, experimental jazz` | **Jazz** | `0.659` |
| 4 | FRKWYS Vol. 15: serenitatem | Visible Cloaks | `ambient, drone, experimental` | **Ambient** | `0.698` |
| 5 | Little Sigh | Marika Hackman | `southern gothic, ambient folk` | **Folk / Country** | `0.492` |
| 6 | UNRELATED | Sam Gendel | `` | **Other / Unclassified** | `0.0` |
| 7 | Reflection (I – IV) | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 8 | Tape 2 | Felbm | `ambient jazz` | **Jazz** | `0.647` |
| 9 | Peach | Alabaster DePlume | `ambient jazz` | **Jazz** | `0.647` |
| 10 | Palms | Robohands | `indie jazz, nu jazz, ambient jazz` | **Jazz** | `0.728` |
| 11 | Sleep Games | Pye Corner Audio | `idm, space rock, ambient` | **Electronic** | `0.618` |
| 12 | The Alias Sessions | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 13 | Glancing Backwards: The Dawn Anthology | John Surman | `free jazz, ambient jazz, jazz` | **Jazz** | `0.755` |
| 14 | Libres antes del final | Colleen | `art pop, ambient` | **Ambient** | `0.582` |
| 15 | Flight Instructions | Move 78 | `nu jazz, indie jazz, ambient jazz` | **Jazz** | `0.73` |
| 16 | Graz | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 17 | La sangre iluminada | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 18 | All Encores | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 19 | Surbahar Sleeping Music | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 20 | Species | Bing & Ruth | `ambient, drone, neoclassical, minimalism` | **Ambient** | `0.621` |
| 21 | Rarities - Quartets | Roger Eno | `ambient, neoclassical, minimalism, contemporary classical` | **Ambient** | `0.549` |
| 22 | Oranj | Robohands | `indie jazz, nu jazz, ambient jazz` | **Jazz** | `0.728` |
| 23 | Copernicus - The Good Book of No | Alabaster DePlume | `ambient jazz` | **Jazz** | `0.647` |
| 24 | Resavoir | Resavoir | `experimental jazz, ambient jazz, jazz house` | **Jazz** | `0.695` |
| 25 | It's Always About Love | Ancient Infinity Orchestra | `ambient jazz` | **Jazz** | `0.647` |
| 26 | Old Friends New Friends | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 27 | The Etna Sessions | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 28 | Spaces (Album Sampler) | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 29 | The Versailles Sessions | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 30 | Point Blank | Tony Kofi | `ambient jazz` | **Jazz** | `0.647` |
| 31 | Music for Peace and Harmony | Hiro Ama | `ambient jazz` | **Jazz** | `0.647` |
| 32 | Without Wind, Without Air | Roger Eno | `ambient, neoclassical, minimalism, contemporary classical` | **Ambient** | `0.549` |
| 33 | The Turning Year | Roger Eno | `ambient, neoclassical, minimalism, contemporary classical` | **Ambient** | `0.549` |
| 34 | Quiet Signs | Jessica Pratt | `ambient folk` | **Ambient** | `0.623` |
| 35 | EP02 | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 36 | Music for Saxofone & Bass Guitar | Sam Gendel | `ambient jazz, experimental jazz, nu jazz, indie jazz` | **Jazz** | `0.73` |
| 37 | While The Flood Rages | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 38 | Green (SFX Version) | Hiroshi Yoshimura | `ambient, minimalism, drone` | **Ambient** | `0.7` |
| 39 | Dusk | Robohands | `indie jazz, nu jazz, ambient jazz` | **Jazz** | `0.728` |
| 40 | Lost in Time | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 41 | Symphonie Pacifique | Greg Foat | `ambient jazz, nu jazz, experimental jazz` | **Jazz** | `0.697` |
| 42 | Slime | Marika Hackman | `southern gothic, ambient folk` | **Folk / Country** | `0.492` |
| 43 | Shapes | Robohands | `indie jazz, nu jazz, ambient jazz` | **Jazz** | `0.728` |
| 44 | Modern Country | William Tyler | `ambient folk` | **Ambient** | `0.623` |
| 45 | Lumen | Bill Laurance | `jazz fusion, jazz, nu jazz, ambient jazz` | **Jazz** | `0.767` |
| 46 | EP03 | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 47 | Eno (Original Motion Picture Soundtrack) | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 48 | From Sleep | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 49 | Palaces of Pity | Malibu | `ambient, drone` | **Ambient** | `0.706` |
| 50 | Twin Color, Vol. 1 | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 51 | Quiet Logic | Mixmaster Morris | `idm, ambient` | **Electronic** | `0.563` |
| 52 | EP01 | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 53 | Rarities - Piano | Roger Eno | `ambient, neoclassical, minimalism, contemporary classical` | **Ambient** | `0.549` |
| 54 | Feldman: The Viola in My Life | Morton Feldman | `minimalism, contemporary classical, avant-garde, musique concrète, drone, electroacoustic` | **Ambient** | `0.593` |
| 55 | Tremors in the Static | Vega Trails | `ambient jazz` | **Jazz** | `0.647` |
| 56 | Violet | Robohands | `indie jazz, nu jazz, ambient jazz` | **Jazz** | `0.728` |
| 57 | stillness, softness… (extended dream transition) | Hinako Omori | `ambient` | **Ambient** | `0.644` |
| 58 | Three Worlds: Music From Woolf Works | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 59 | Sigh | Valentin Stip | `` | **Other / Unclassified** | `0.0` |
| 60 | Tripping with Nils Frahm | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 61 | Earth Patterns | Szun Waves | `ambient jazz, nu jazz, experimental jazz, indie jazz` | **Jazz** | `0.732` |
| 62 | Zimpel / Ziolek | Jakub Ziolek | `` | **Other / Unclassified** | `0.0` |
| 63 | Arpo | Call Super | `idm` | **Electronic** | `0.371` |
| 64 | Encores 1 | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 65 | Sun Arcs | Blue Lake | `ambient, ambient jazz` | **Ambient** | `0.665` |
| 66 | Seeing Through Sound (Pentimento Volume Two) | Jon Hassell | `ambient jazz, ambient, minimalism, experimental jazz, electroacoustic, drone, musique concrète, avant-garde` | **Jazz** | `0.73` |
| 67 | Lex | Visible Cloaks | `ambient, drone, experimental` | **Ambient** | `0.698` |
| 68 | Brian Eno - Film Music 1976 ~ 2020 | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 69 | Jessica Pratt | Jessica Pratt | `ambient folk` | **Ambient** | `0.623` |
| 70 | In The Age Of Data | Move 78 | `nu jazz, indie jazz, ambient jazz` | **Jazz** | `0.73` |
| 71 | Ill Considered III | Ill Considered | `nu jazz, free jazz, experimental jazz, ambient jazz, jazz, indie jazz, jazz fusion` | **Jazz** | `0.808` |
| 72 | The Algorithm Smiles Upon You | Move 78 | `nu jazz, indie jazz, ambient jazz` | **Jazz** | `0.73` |
| 73 | Le jour et la nuit du réel | Colleen | `art pop, ambient` | **Ambient** | `0.582` |
| 74 | WILKES | Sam Wilkes | `ambient jazz, nu jazz, experimental jazz, indie jazz` | **Jazz** | `0.732` |
| 75 | The Greater Wings | Julie Byrne | `ambient folk` | **Ambient** | `0.623` |
| 76 | Game Four | Move 78 | `nu jazz, indie jazz, ambient jazz` | **Jazz** | `0.73` |
| 77 | N-Plants | Biosphere | `ambient, drone, idm, space music, dark ambient, electroacoustic` | **Ambient** | `0.736` |
| 78 | Top Boy (Score from the Original Series) | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 79 | The Jewel In The Lotus | Bennie Maupin | `free jazz, ambient jazz, jazz fusion, jazz funk, experimental jazz` | **Jazz** | `0.81` |
| 80 | Pharoah | Pharoah Sanders | `free jazz, ambient jazz, jazz, experimental jazz, hard bop` | **Jazz** | `0.776` |
| 81 | Empty | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 82 | Different Trains / Electric Counterpoint | Steve Reich | `minimalism, contemporary classical, avant-garde, musique concrète, electroacoustic, classical, experimental, ambient` | **Classical** | `0.599` |
| 83 | Late Night Tales Nils Frahm | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 84 | Ambient 4: On Land (Remastered 2004) | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 85 | Substrata 2 | Biosphere | `ambient, drone, idm, space music, dark ambient, electroacoustic` | **Ambient** | `0.736` |
| 86 | Ptah The El Daoud | Alice Coltrane | `free jazz, jazz, experimental jazz, ambient jazz` | **Jazz** | `0.782` |
| 87 | Bohren for Beginners | Bohren & Der Club Of Gore | `ambient jazz, dark ambient, drone, experimental jazz, ambient` | **Ambient** | `0.747` |
| 88 | Kakashi | Yasuaki Shimizu | `ambient` | **Ambient** | `0.644` |
| 89 | Soundscapes Vol. 1 - Music for Harlequins | Gianni Brezzo | `nu jazz, ambient jazz, indie jazz, jazz funk` | **Jazz** | `0.727` |
| 90 | Le plan de Paris | Pascal Comelade | `musique concrète` | **Jazz** | `0.354` |
| 91 | Statea | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 92 | Tender Opposites | TOPS | `` | **Other / Unclassified** | `0.0` |
| 93 | Robyn | cktrl | `ambient jazz` | **Jazz** | `0.647` |
| 94 | Screws Reworked | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 95 | Anicca | Teebs | `idm` | **Electronic** | `0.371` |
| 96 | Oneohtrix Point Never - Scores | Oneohtrix Point Never | `plunderphonics, idm, ambient, drone, experimental, vaporwave` | **Ambient** | `0.591` |
| 97 | Recomposed By Max Richter: Vivaldi, The Four Seasons | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 98 | Radio Amor | Tim Hecker | `drone, ambient, electroacoustic, idm, dark ambient, experimental, minimalism` | **Ambient** | `0.72` |
| 99 | Cascade | Floating Points | `idm, ambient jazz, gnawa` | **Electronic** | `0.632` |
| 100 | Toward The Within (Remastered) | Dead Can Dance | `neofolk, darkwave, gothic rock, deathrock, neoclassical, post-punk, new age, cold wave` | **Punk / Alternative** | `0.711` |
| 101 | Mighty Vertebrate | Anna Butterss | `ambient jazz, indie jazz, experimental jazz` | **Jazz** | `0.709` |
| 102 | Wrong Way Up [Expanded Edition] | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 103 | Again | Oneohtrix Point Never | `plunderphonics, idm, ambient, drone, experimental, vaporwave` | **Ambient** | `0.591` |
| 104 | sentiment | claire rousay | `musique concrète, electroacoustic, ambient, drone, experimental` | **Ambient** | `0.608` |
| 105 | Music Has The Right To Children | Boards of Canada | `idm, ambient, trip hop, downtempo, electronic` | **Electronic** | `0.677` |
| 106 | Crush | Floating Points | `idm, ambient jazz, gnawa` | **Electronic** | `0.632` |
| 107 | The Blue Notebooks (15 Years) | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 108 | Quique Redux (2025 Remaster) | Seefeel | `idm, shoegaze, post-rock, ambient, drone` | **Electronic** | `0.625` |
| 109 | Little Oblivions | Julien Baker | `ambient folk` | **Ambient** | `0.623` |
| 110 | Marty Supreme (Original Soundtrack) | Daniel Lopatin | `score, drone` | **Ambient** | `0.313` |
| 111 | PHANTOM BRICKWORKS | Bibio | `ambient folk, downtempo` | **Ambient** | `0.532` |
| 112 | Warm Chris | Aldous Harding | `ambient folk` | **Ambient** | `0.623` |
| 113 | Midwinter Swimmers | The Innocence Mission | `ambient folk` | **Ambient** | `0.623` |
| 114 | Sam Wilkes, Craig Weinrib, and Dylan Day | Sam Wilkes | `ambient jazz, nu jazz, experimental jazz, indie jazz` | **Jazz** | `0.732` |
| 115 | Paradessence | Visible Cloaks | `ambient, drone, experimental` | **Ambient** | `0.698` |
| 116 | Flora | Hiroshi Yoshimura | `ambient, minimalism, drone` | **Ambient** | `0.7` |
| 117 | Mixing Colours (Expanded) | Roger Eno | `ambient, neoclassical, minimalism, contemporary classical` | **Ambient** | `0.549` |
| 118 | Mi Media Naranja | Labradford | `post-rock, drone, ambient, slowcore` | **Ambient** | `0.66` |
| 119 | Sleep | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 120 | ICONOCLASTS | Anna von Hausswolff | `neofolk, drone, art pop` | **Ambient** | `0.468` |
| 121 | Anoyo | Tim Hecker | `drone, ambient, electroacoustic, idm, dark ambient, experimental, minimalism` | **Ambient** | `0.72` |
| 122 | Late Night Tales: Jon Hopkins | Jon Hopkins | `idm, ambient` | **Electronic** | `0.563` |
| 123 | Here in the Pitch | Jessica Pratt | `ambient folk` | **Ambient** | `0.623` |
| 124 | Haunt Me | Tim Hecker | `drone, ambient, electroacoustic, idm, dark ambient, experimental, minimalism` | **Ambient** | `0.72` |
| 125 | Magic Oneohtrix Point Never | Oneohtrix Point Never | `plunderphonics, idm, ambient, drone, experimental, vaporwave` | **Ambient** | `0.591` |
| 126 | Shall We Go On Sinning So That Grace May Increase? | The Soft Pink Truth | `ambient, idm` | **Electronic** | `0.556` |
| 127 | Captain Of None | Colleen | `art pop, ambient` | **Ambient** | `0.582` |
| 128 | Uhlmann Johnson Wilkes | Gregory Uhlmann | `ambient jazz, ambient folk, experimental jazz` | **Ambient** | `0.665` |
| 129 | Space 1.8 | Nala Sinephro | `ambient jazz, ambient, experimental jazz, nu jazz` | **Jazz** | `0.708` |
| 130 | Music for Nine Post Cards | Hiroshi Yoshimura | `ambient, minimalism, drone` | **Ambient** | `0.7` |
| 131 | Designer | Aldous Harding | `ambient folk` | **Ambient** | `0.623` |
| 132 | boygenius | Julien Baker | `ambient folk` | **Ambient** | `0.623` |
| 133 | Any Human Friend | Marika Hackman | `southern gothic, ambient folk` | **Folk / Country** | `0.492` |
| 134 | Ambient 1: Music For Airports (Remastered 2004) | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 135 | Singularity | Jon Hopkins | `idm, ambient` | **Electronic** | `0.563` |
| 136 | Cheetah EP | Aphex Twin | `idm, ambient` | **Electronic** | `0.563` |
| 137 | Good Time Original Motion Picture Soundtrack | Oneohtrix Point Never | `plunderphonics, idm, ambient, drone, experimental, vaporwave` | **Ambient** | `0.591` |
| 138 | Apollo | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 139 | Reassemblage | Visible Cloaks | `ambient, drone, experimental` | **Ambient** | `0.698` |
| 140 | AZD | Actress | `idm, ambient, experimental` | **Electronic** | `0.532` |
| 141 | Endlessness | Nala Sinephro | `ambient jazz, ambient, experimental jazz, nu jazz` | **Jazz** | `0.708` |
| 142 | Drukqs | Aphex Twin | `idm, ambient` | **Electronic** | `0.563` |
| 143 | EARS | Kaitlyn Aurelia Smith | `ambient, art pop, experimental` | **Ambient** | `0.594` |
| 144 | Tranquilizer | Oneohtrix Point Never | `plunderphonics, idm, ambient, drone, experimental, vaporwave` | **Ambient** | `0.591` |
| 145 | stillness, softness… | Hinako Omori | `ambient` | **Ambient** | `0.644` |
| 146 | Instrumental Tourist | Tim Hecker | `drone, ambient, electroacoustic, idm, dark ambient, experimental, minimalism` | **Ambient** | `0.72` |
| 147 | Herd of Instinct | .O.rang | `post-rock, musique concrète, krautrock` | **Rock** | `0.554` |
| 148 | Tragic Magic | Julianna Barwick | `ambient, drone, art pop` | **Ambient** | `0.724` |
| 149 | Liminal | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 150 | Ravedeath, 1972 | Tim Hecker | `drone, ambient, electroacoustic, idm, dark ambient, experimental, minimalism` | **Ambient** | `0.72` |
| 151 | Age Of | Oneohtrix Point Never | `plunderphonics, idm, ambient, drone, experimental, vaporwave` | **Ambient** | `0.591` |
| 152 | Promises | Floating Points | `idm, ambient jazz, gnawa` | **Electronic** | `0.632` |
| 153 | Atlas | Laurel Halo | `art pop, ambient, drone, experimental, electroacoustic, idm` | **Electronic** | `0.702` |
| 154 | async | Ryuichi Sakamoto | `japanese classical, ambient, minimalism` | **Ambient** | `0.533` |
| 155 | Ambivalence Avenue | Bibio | `ambient folk, downtempo` | **Ambient** | `0.532` |
| 156 | Suite for Max Brown | Jeff Parker | `ambient jazz, experimental jazz, free jazz, nu jazz` | **Jazz** | `0.76` |
| 157 | Shade | Grouper | `drone, ambient, slowcore, dream pop` | **Ambient** | `0.72` |
| 158 | Listening To Pictures (Pentimento Volume One) | Jon Hassell | `` | **Other / Unclassified** | `0.0` |
| 159 | Karma & Desire | Actress | `idm, ambient, experimental` | **Electronic** | `0.532` |
| 160 | On Your Own Love Again | Jessica Pratt | `ambient folk` | **Ambient** | `0.623` |
| 161 | Sol.Hz | Seefeel | `idm, shoegaze, post-rock, ambient, drone` | **Electronic** | `0.625` |
| 162 | A Mineral Love | Bibio | `ambient folk, downtempo` | **Ambient** | `0.532` |
| 163 | Not Even Happiness | Julie Byrne | `ambient folk` | **Ambient** | `0.623` |
| 164 | All Melody | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 165 | Ambient 2: The Plateaux Of Mirror (Remastered 2004) | Harold Budd | `ambient, minimalism, shoegaze` | **Ambient** | `0.548` |
| 166 | New Energy | Four Tet | `idm, electronica` | **Electronic** | `0.582` |
| 167 | Fidelity | The Durutti Column | `madchester, art rock, post-punk` | **Punk / Alternative** | `0.625` |
| 168 | Twin Color (Extended Play No. 2) | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 169 | Day-blind | Gabriel Brady | `ambient folk, experimental` | **Ambient** | `0.639` |
| 170 | Rifts | Oneohtrix Point Never | `` | **Other / Unclassified** | `0.0` |
| 171 | The Undivided Five | A Winged Victory for the Sullen | `ambient, neoclassical, drone, minimalism, contemporary classical` | **Ambient** | `0.606` |
| 172 | Dragging a Dead Deer Up a Hill | Grouper | `drone, ambient, slowcore, dream pop` | **Ambient** | `0.72` |
| 173 | Telas | Nicolas Jaar | `downtempo, electronica` | **Electronic** | `0.427` |
| 174 | Cosmos | Murcof | `idm, ambient, dark ambient, glitch, drone, space music, electronic classical` | **Electronic** | `0.701` |
| 175 | Love + Light | Daniel Avery | `idm, acid house` | **Electronic** | `0.383` |
| 176 | 1996 | Ryuichi Sakamoto | `japanese classical, ambient, minimalism` | **Ambient** | `0.533` |
| 177 | The Ship | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 178 | Solo | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 179 | The Closest Thing to Silence | Ariel Kalma | `new age, ambient, electroacoustic, drone, ambient jazz` | **Ambient** | `0.715` |
| 180 | The New Four Seasons - Vivaldi Recomposed | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 181 | I'm Not Your Man (Deluxe) | Marika Hackman | `` | **Other / Unclassified** | `0.0` |
| 182 | LUX | ROSALÍA | `latin` | **Latin / World** | `0.412` |
| 183 | Small Craft | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 184 | Salute to the Sun | Matthew Halsall | `ambient jazz, jazz, nu jazz, indie jazz` | **Jazz** | `0.735` |
| 185 | choke enough | Oklou | `art pop, hyperpop` | **Pop** | `0.474` |
| 186 | KiTsuNe / Brian the Fox | The Future Eve | `progressive rock` | **Rock** | `0.658` |
| 187 | Grains | Move 78 | `` | **Other / Unclassified** | `0.0` |
| 188 | Jetty (Original Motion Picture Soundtrack) | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 189 | Quarantine | Laurel Halo | `art pop, ambient, drone, experimental, electroacoustic, idm` | **Electronic** | `0.702` |
| 190 | Contre-Temps | Flavien Berger | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 191 | Garden Of Delete | Oneohtrix Point Never | `plunderphonics, idm, ambient, drone, experimental, vaporwave` | **Ambient** | `0.591` |
| 192 | GOOD SPORT | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 193 | Quiet Forest | Hiroshi Yoshimura | `ambient, minimalism, drone` | **Ambient** | `0.7` |
| 194 | Pink | Four Tet | `idm, electronica` | **Electronic** | `0.582` |
| 195 | Eternity | Alice Coltrane | `free jazz, jazz, experimental jazz, ambient jazz` | **Jazz** | `0.782` |
| 196 | Chimet | MINING | `ambient, drone, experimental` | **Ambient** | `0.698` |
| 197 | Small Craft On A Milk Sea | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 198 | Party | Aldous Harding | `ambient folk` | **Ambient** | `0.623` |
| 199 | Everyone Alive Wants Answers | Colleen | `art pop, ambient` | **Ambient** | `0.582` |
| 200 | Visible Cloaks | Visible Cloaks | `ambient, drone, experimental` | **Ambient** | `0.698` |
| 201 | Spirit of Eden | Talk Talk | `new wave, synthpop` | **Electronic** | `0.493` |
| 202 | Will | Julianna Barwick | `ambient, drone, art pop` | **Ambient** | `0.724` |
| 203 | Discreet Music | Brian Eno | `ambient, krautrock, art rock, minimalism, drone, glam rock, space music` | **Rock** | `0.718` |
| 204 | Train on the Island | Aldous Harding | `ambient folk` | **Ambient** | `0.623` |
| 205 | Songs From Before | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 206 | Sleep Circle | Max Richter | `neoclassical, contemporary classical, minimalism, ambient, classical` | **Classical** | `0.484` |
| 207 | Green | Hiroshi Yoshimura | `ambient, minimalism, drone` | **Ambient** | `0.7` |
| 208 | Love Streams | Tim Hecker | `drone, ambient, electroacoustic, idm, dark ambient, experimental, minimalism` | **Ambient** | `0.72` |
| 209 | Raw Silk Uncut Wood | Laurel Halo | `art pop, ambient, drone, experimental, electroacoustic, idm` | **Electronic** | `0.702` |
| 210 | Nothing Is Still | Leon Vynehall | `lo-fi house, deep house` | **Electronic** | `0.216` |
| 211 | A flame my love, a frequency | Colleen | `art pop, ambient` | **Ambient** | `0.582` |
| 212 | No Home of the Mind | Bing & Ruth | `ambient, drone, neoclassical, minimalism` | **Ambient** | `0.621` |
| 213 | Raven | Kelela | `alternative r&b` | **R&B / Soul** | `0.352` |
| 214 | Turn Out the Lights | Julien Baker | `ambient folk` | **Ambient** | `0.623` |
| 215 | Zuckerzeit | Cluster | `krautrock, ambient, space rock, drone, avant-garde` | **Rock** | `0.648` |
| 216 | Utopia | Björk | `art pop, trip hop` | **Hip-Hop** | `0.561` |
| 217 | Surround | Hiroshi Yoshimura | `ambient, minimalism, drone` | **Ambient** | `0.7` |
| 218 | The Kid | Kaitlyn Aurelia Smith | `ambient, art pop, experimental` | **Ambient** | `0.594` |
| 219 | Inferno | Boards of Canada | `idm, ambient, trip hop, downtempo, electronic` | **Electronic** | `0.677` |
| 220 | Spaces | Nils Frahm | `neoclassical, contemporary classical, minimalism, ambient` | **Ambient** | `0.546` |
| 221 | Fourth World Vol 1 Possible Musics | Jon Hassell | `ambient jazz, ambient, minimalism, experimental jazz, electroacoustic, drone, musique concrète, avant-garde` | **Jazz** | `0.73` |
| 222 | Disraeli Gears | Cream | `classic rock, psychedelic rock, acid rock, blues rock` | **Rock** | `0.715` |
| 223 | Lazaretto | Jack White | `blues rock, garage rock` | **Blues** | `0.553` |
| 224 | Mule Variations (Remastered) | Tom Waits | `singer-songwriter, southern gothic` | **R&B / Soul** | `0.42` |
| 225 | Fear Of The Dawn | Jack White | `blues rock, garage rock` | **Blues** | `0.553` |
| 226 | No Name | Jack White | `blues rock, garage rock` | **Blues** | `0.553` |
| 227 | Entering Heaven Alive | Jack White | `blues rock, garage rock` | **Blues** | `0.553` |
| 228 | Late Night Tales: Belle and Sebastian, Vol. 2 (Sampler) | Belle and Sebastian | `baroque pop` | **Pop** | `0.548` |
| 229 | Interior Live Oak | Cass McCombs | `baroque pop, singer-songwriter` | **Pop** | `0.537` |
| 230 | re:works - EP | Pascal Rogé | `impressionism, classical piano, classical` | **Classical** | `0.552` |
| 231 | The Cradle | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 232 | Pur ti miro | Wu Wei | `japanese classical` | **Classical** | `0.488` |
| 233 | At Best Cuckold | Avi Buffalo | `baroque pop` | **Pop** | `0.548` |
| 234 | Messiaen: Organ Works | Olivier Messiaen | `contemporary classical, avant-garde, musique concrète, electroacoustic, expressionism` | **Classical** | `0.573` |
| 235 | Messiaen: Preludes / 4 Rhythmic Studies / Canteyodjaya | Olivier Messiaen | `contemporary classical, avant-garde, musique concrète, electroacoustic, expressionism` | **Classical** | `0.573` |
| 236 | Bel Canto: The Voice of the Viola | Antoine Tamestit | `chamber music, classical, concerto` | **Classical** | `0.725` |
| 237 | Sticky Wickets | The Duckworth Lewis Method | `baroque pop, comedy` | **Classical** | `0.517` |
| 238 | Worst Christmas Ever! | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 239 | Glass: Heroes Symphony | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 240 | Digital Nomad | Ducktails | `` | **Other / Unclassified** | `0.0` |
| 241 | Ypres | Tindersticks | `baroque pop` | **Pop** | `0.548` |
| 242 | Gavin Bryards : Allegrasco - Alaric I or II - Three Elegics | Gavin Bryars | `minimalism, contemporary classical, avant-garde, electroacoustic` | **Ambient** | `0.485` |
| 243 | Blackberry | Peter Broderick | `neoclassical, contemporary classical, minimalism` | **Classical** | `0.317` |
| 244 | Messiaen: Les corps glorieux, I/20 & Messe de la Pentecôte, I/36 | Olivier Messiaen | `contemporary classical, avant-garde, musique concrète, electroacoustic, expressionism` | **Classical** | `0.573` |
| 245 | Office Politics | The Divine Comedy | `baroque pop, britpop, comedy` | **Pop** | `0.547` |
| 246 | Adès: Asyla, Tevot, Polaris | Thomas Adès | `contemporary classical` | **Classical** | `0.571` |
| 247 | Always a Stranger | Tindersticks | `baroque pop` | **Pop** | `0.548` |
| 248 | Daffy Duck in Hollwood (Remastered) | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 249 | Messiaen: The Organ Works | Olivier Messiaen | `contemporary classical, avant-garde, musique concrète, electroacoustic, expressionism` | **Classical** | `0.573` |
| 250 | Truth in Our Time | Canada's National Arts Centre Orchestra | `contemporary classical, baroque` | **Classical** | `0.66` |
| 251 | Métode De Rocanrol | Pascal Comelade | `musique concrète` | **Jazz** | `0.354` |
| 252 | The Panufnik Legacies II | London Symphony Orchestra | `classical, orchestral, ballet, opera` | **Classical** | `0.775` |
| 253 | Seed Cake On Leap Year | Cass McCombs | `baroque pop, singer-songwriter` | **Pop** | `0.537` |
| 254 | Bach, J.S.: Christmas Oratorio; St. Matthew Passion; St. John Passion; Mass in B minor | Johann Sebastian Bach | `baroque, classical, concerto, classical piano, early music, chamber music` | **Classical** | `0.875` |
| 255 | Harmonium/Choruses from The Death Of Klinghoffer | John Adams | `minimalism, contemporary classical, avant-garde, opera` | **Classical** | `0.568` |
| 256 | Glass Gaze | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 257 | Glass: Symphony No. 4, 'Heroes' / The Light | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 258 | Drift (Remastered) | The Apartments | `jangle pop, baroque pop` | **Pop** | `0.525` |
| 259 | Tchaikovsky: Ballet Suites (Swan Lake; The Sleeping Beauty; The Nutcraker) | Pyotr Ilyich Tchaikovsky | `ballet, classical, concerto, orchestral` | **Classical** | `0.708` |
| 260 | Rough Trade Session | Weyes Blood | `art pop, baroque pop` | **Pop** | `0.611` |
| 261 | Lamentations | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 262 | Demoed | Lambchop | `alt country, baroque pop, americana` | **Pop** | `0.563` |
| 263 | Messiaen: Turangalila Symphony / L'Ascension | Olivier Messiaen | `contemporary classical, avant-garde, musique concrète, electroacoustic, expressionism` | **Classical** | `0.573` |
| 264 | Wish Hotel | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 265 | Ramapo River Anthology | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 266 | http://www.itstartshear.com | Peter Broderick | `neoclassical, contemporary classical, minimalism` | **Classical** | `0.317` |
| 267 | Love Yourself / With My Whole Heart | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 268 | Preludes by Chopin, Bach, Rachmaninoff, Messiaen, Górecki | Jan Lisiecki | `classical piano, classical` | **Classical** | `0.553` |
| 269 | This is Mozart | Wolfgang Amadeus Mozart | `classical, classical piano, opera, chamber music, concerto` | **Classical** | `0.822` |
| 270 | Messiaen: La Nativité du Seigneur | Olivier Messiaen | `contemporary classical, avant-garde, musique concrète, electroacoustic, expressionism` | **Classical** | `0.573` |
| 271 | Figures of Glass (Piano Etudes - Edits) | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 272 | Bolcom: 12 New Etudes/Wolpe: Battle Piece | Marc-André Hamelin | `classical piano, minimalism, classical, chamber music, impressionism` | **Classical** | `0.707` |
| 273 | Bartók: Concerto for Orchestra; Orchestral Pieces, Op. 12 | Béla Bartók | `classical, expressionism, neoclassical, concerto, contemporary classical` | **Classical** | `0.681` |
| 274 | Soft Tissue | Tindersticks | `baroque pop` | **Pop** | `0.548` |
| 275 | Georg Philipp Telemann: Viola Concertos - Overtures - Fantasias | Georg Philipp Telemann | `baroque, concerto, classical, chamber music` | **Classical** | `0.834` |
| 276 | After The Requiem | Gavin Bryars | `minimalism, contemporary classical, avant-garde, electroacoustic` | **Ambient** | `0.485` |
| 277 | Chopin: Nocturnes - Sony Classical Originals | Frédéric Chopin | `classical piano, classical` | **Classical** | `0.553` |
| 278 | Thunderclouds | Louis Philippe | `baroque pop, jangle pop, shibuya-kei` | **Pop** | `0.546` |
| 279 | Novö Piano | Maxence Cyrin | `` | **Other / Unclassified** | `0.0` |
| 280 | Wagner: Overtures and Preludes | Richard Wagner | `opera, classical` | **Classical** | `0.618` |
| 281 | Silent Hour / Golden Mile | Daniel Rossen | `baroque pop` | **Pop** | `0.548` |
| 282 | White Is Relic/Irrealis Mood | of Montreal | `neo-psychedelic, baroque pop, art pop` | **Pop** | `0.684` |
| 283 | Peter Broderick & Friends Play Arthur Russell | Peter Broderick | `neoclassical, contemporary classical, minimalism` | **Classical** | `0.317` |
| 284 | Philip Glass: Music In 12 Parts | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 285 | St. Catherine | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 286 | Eighth Grade (Original Motion Picture Soundtrack) | Anna Meredith | `contemporary classical` | **Classical** | `0.571` |
| 287 | A Descent into the Maelström | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 288 | Le Mystere Des Voix Bulgares: Ritual | Bulgarian State Television Female Choir | `choral` | **Classical** | `0.507` |
| 289 | Rainy Sunday Afternoon | The Divine Comedy | `baroque pop, britpop, comedy` | **Pop** | `0.547` |
| 290 | The Machine That Made Us | Flotation Toy Warning | `neo-psychedelic, baroque pop, space rock` | **Rock** | `0.674` |
| 291 | Johann Strauss II.: Most Famous Waltzes | Strauss Festival Orchestra | `classical` | **Classical** | `0.561` |
| 292 | Ducktails III: Arcade Dynamics | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 293 | Koyaanisqatsi (Complete Original Soundtrack) | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 294 | Pierre Henry: Messe Pour Le Temps Present | Pierre Henry | `musique concrète, electroacoustic, avant-garde, experimental, contemporary classical` | **Classical** | `0.548` |
| 295 | Philip Glass: The Complete Piano Etudes | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 296 | The Lateness Of The Hour | Eric Matthews | `baroque pop, power pop` | **Pop** | `0.55` |
| 297 | III: Arcade Dynamics | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 298 | Begin | The Millennium | `baroque pop` | **Pop** | `0.548` |
| 299 | Koyaanisqatsi (Soundtrack) | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 300 | Philip Glass: Piano Etudes Versions | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 301 | Prefection | Cass McCombs | `baroque pop, singer-songwriter` | **Pop** | `0.537` |
| 302 | lousy with sylvianbriar | of Montreal | `neo-psychedelic, baroque pop, art pop` | **Pop** | `0.684` |
| 303 | Philip Glass: Solo Piano | Philip Glass | `minimalism, contemporary classical, classical, neoclassical` | **Classical** | `0.41` |
| 304 | Delius: On Hearing the First Cuckoo in Spring | Frederick Delius | `impressionism, classical` | **Classical** | `0.385` |
| 305 | Wainwright: Dream Requiem | Rufus Wainwright | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 306 | Jersey Devil | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 307 | Veckatimest | Grizzly Bear | `indie, baroque pop, indie rock` | **Pop** | `0.756` |
| 308 | Flotus | Lambchop | `alt country, baroque pop, americana` | **Pop** | `0.563` |
| 309 | Heartmind | Cass McCombs | `baroque pop, singer-songwriter` | **Pop** | `0.537` |
| 310 | Have You In My Wilderness | Julia Holter | `art pop, baroque pop` | **Pop** | `0.611` |
| 311 | Late Night Tales: Belle and Sebastian | Belle and Sebastian | `baroque pop` | **Pop** | `0.548` |
| 312 | Foreverland | The Divine Comedy | `baroque pop, britpop, comedy` | **Pop** | `0.547` |
| 313 | Cardinal | Cardinal | `baroque pop, power pop` | **Pop** | `0.55` |
| 314 | The Ascension | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 315 | Partners | Peter Broderick | `neoclassical, contemporary classical, minimalism` | **Classical** | `0.317` |
| 316 | The Bible | Lambchop | `alt country, baroque pop, americana` | **Pop** | `0.563` |
| 317 | Aporia | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 318 | Lady On The Cusp | of Montreal | `neo-psychedelic, baroque pop, art pop` | **Pop** | `0.684` |
| 319 | Odessey and Oracle | The Zombies | `baroque pop, psychedelic rock` | **Rock** | `0.626` |
| 320 | Innocence Reaches | of Montreal | `neo-psychedelic, baroque pop, art pop` | **Pop** | `0.684` |
| 321 | Aviary | Julia Holter | `art pop, baroque pop` | **Pop** | `0.611` |
| 322 | My Finest Work Yet | Andrew Bird | `baroque pop, indie folk` | **Pop** | `0.658` |
| 323 | Javelin | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 324 | And In The Darkness, Hearts Aglow | Weyes Blood | `art pop, baroque pop` | **Pop** | `0.611` |
| 325 | Colours Of The Night | Peter Broderick | `neoclassical, contemporary classical, minimalism` | **Classical** | `0.317` |
| 326 | Simple Pleasure | Tindersticks | `baroque pop` | **Pop** | `0.548` |
| 327 | The Greatest Gift | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 328 | Father of the Bride | Vampire Weekend | `indie, baroque pop` | **Pop** | `0.685` |
| 329 | Carrie & Lowell (10th Anniversary Edition) | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 330 | Late Night Tales: Ólafur Arnalds | Ólafur Arnalds | `neoclassical, contemporary classical, minimalism` | **Classical** | `0.317` |
| 331 | Distractions | Tindersticks | `baroque pop` | **Pop** | `0.548` |
| 332 | Only God Was Above Us | Vampire Weekend | `indie, baroque pop` | **Pop** | `0.685` |
| 333 | The Life Pursuit | Belle and Sebastian | `baroque pop` | **Pop** | `0.548` |
| 334 | Mangy Love | Cass McCombs | `baroque pop, singer-songwriter` | **Pop** | `0.537` |
| 335 | Wit's End | Cass McCombs | `baroque pop, singer-songwriter` | **Pop** | `0.537` |
| 336 | How To Solve Our Human Problems (Part 1) | Belle and Sebastian | `baroque pop` | **Pop** | `0.548` |
| 337 | How to Solve Our Human Problems (Part 2) | Belle and Sebastian | `baroque pop` | **Pop** | `0.548` |
| 338 | In The Same Room | Julia Holter | `art pop, baroque pop` | **Pop** | `0.611` |
| 339 | Girls in Peacetime Want to Dance | Belle and Sebastian | `baroque pop` | **Pop** | `0.548` |
| 340 | Dr Dee | Damon Albarn | `` | **Other / Unclassified** | `0.0` |
| 341 | Damaged | Lambchop | `alt country, baroque pop, americana` | **Pop** | `0.563` |
| 342 | What A Terrible World, What A Beautiful World | The Decemberists | `baroque pop, indie folk` | **Pop** | `0.658` |
| 343 | The Future and the Past | Natalie Prass | `baroque pop` | **Pop** | `0.548` |
| 344 | Hang | Foxygen | `baroque pop, neo-psychedelic` | **Pop** | `0.604` |
| 345 | HARK! | Andrew Bird | `baroque pop, indie folk` | **Pop** | `0.658` |
| 346 | Late Developers | Belle and Sebastian | `baroque pop` | **Pop** | `0.548` |
| 347 | The Innocents | Weyes Blood | `art pop, baroque pop` | **Pop** | `0.611` |
| 348 | Carrie & Lowell | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 349 | A Bit of Previous | Belle and Sebastian | `baroque pop` | **Pop** | `0.548` |
| 350 | You Belong There | Daniel Rossen | `baroque pop` | **Pop** | `0.548` |
| 351 | Painted Ruins | Grizzly Bear | `indie, baroque pop, indie rock` | **Pop** | `0.756` |
| 352 | The Waiting Room | Tindersticks | `baroque pop` | **Pop** | `0.548` |
| 353 | I Trawl the Megahertz | Prefab Sprout | `` | **Other / Unclassified** | `0.0` |
| 354 | The Jazz Age | Jack | `britpop, baroque pop, madchester` | **Pop** | `0.594` |
| 355 | Varmints | Anna Meredith | `contemporary classical` | **Classical** | `0.571` |
| 356 | Seeing Other People | Foxygen | `baroque pop, neo-psychedelic` | **Pop** | `0.604` |
| 357 | Showtunes | Lambchop | `alt country, baroque pop, americana` | **Pop** | `0.563` |
| 358 | Further | Richard Hawley | `baroque pop, singer-songwriter` | **Pop** | `0.537` |
| 359 | Something in the Room She Moves | Julia Holter | `art pop, baroque pop` | **Pop** | `0.611` |
| 360 | Orphée | Jóhann Jóhannsson | `neoclassical, contemporary classical, minimalism, score` | **Classical** | `0.403` |
| 361 | Let's Pretend | Louis Philippe | `baroque pop, jangle pop, shibuya-kei` | **Pop** | `0.546` |
| 362 | Impressions | Ducktails | `chillwave, baroque pop, dream pop` | **Pop** | `0.628` |
| 363 | Bumps Per Minute (18 Studies for Dodgems) | Anna Meredith | `contemporary classical` | **Classical** | `0.571` |
| 364 | Life Will See You Now | Jens Lekman | `baroque pop, swedish pop` | **Pop** | `0.585` |
| 365 | Reflections | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 366 | Closure | Piano Magic | `post-rock, baroque pop, slowcore, dream pop` | **Pop** | `0.683` |
| 367 | U.F.O. | Jim Sullivan | `baroque pop` | **Pop** | `0.548` |
| 368 | The Something Rain | Tindersticks | `baroque pop` | **Pop** | `0.548` |
| 369 | No Other | Gene Clark | `country rock, baroque pop, folk rock, americana` | **Rock** | `0.661` |
| 370 | Titanic Rising | Weyes Blood | `art pop, baroque pop` | **Pop** | `0.611` |
| 371 | UR FUN | of Montreal | `neo-psychedelic, baroque pop, art pop` | **Pop** | `0.684` |
| 372 | FIBS | Anna Meredith | `contemporary classical` | **Classical** | `0.571` |
| 373 | Tip of the Sphere | Cass McCombs | `baroque pop, singer-songwriter` | **Pop** | `0.537` |
| 374 | aethermead | of Montreal | `neo-psychedelic, baroque pop, art pop` | **Pop** | `0.684` |
| 375 | No Treasure But Hope | Tindersticks | `baroque pop` | **Pop** | `0.548` |
| 376 | This (Is What I Wanted to Tell You) | Lambchop | `alt country, baroque pop, americana` | **Pop** | `0.563` |
| 377 | Days Of Future Passed (Expanded Edition) | The Moody Blues | `progressive rock, art rock, psychedelic rock, baroque pop` | **Rock** | `0.812` |
| 378 | Hug Of Thunder | Broken Social Scene | `baroque pop, indie rock, indie` | **Pop** | `0.741` |
| 379 | Did you know that there's a tunnel under Ocean Blvd | Lana Del Rey | `` | **Other / Unclassified** | `0.0` |
| 380 | A Beginner's Mind | Sufjan Stevens | `baroque pop` | **Pop** | `0.548` |
| 381 | Paint Your Wagon (Music From The Soundtrack) | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 382 | Dreamstate | Kelly Lee Owens | `` | **Other / Unclassified** | `0.0` |
| 383 | Miniatures de auto rhythm | Domenique Dumont | `` | **Other / Unclassified** | `0.0` |
| 384 | Filmmusik Anthology 6 | Irmin Schmidt | `krautrock, avant-garde` | **Rock** | `0.491` |
| 385 | Elevators: Act I & II | Bishop Nehru | `` | **Other / Unclassified** | `0.0` |
| 386 | Countdown: 1992-1983 | Pulp | `britpop` | **Pop** | `0.359` |
| 387 | the afterparty | Andy Shauf | `` | **Other / Unclassified** | `0.0` |
| 388 | All Your Life You Walk | Carlos Cipa | `neoclassical` | **Other / Unclassified** | `0.247` |
| 389 | Woke Up Sticky…Plus | Peter Perrett | `` | **Other / Unclassified** | `0.0` |
| 390 | Februar Mood | Eden Ahbez | `exotica, spoken word` | **Other / Unclassified** | `0.312` |
| 391 | Another Helping of The Sweet Enoughs | The Sweet Enoughs | `exotica` | **Other / Unclassified** | `0.297` |
| 392 | Impossible Dream | Haley Bonar | `` | **Other / Unclassified** | `0.0` |
| 393 | MESTIZX | Ibelisse Guardia Ferragutti | `` | **Other / Unclassified** | `0.0` |
| 394 | Archives | Vanishing Twin | `neo-psychedelic` | **Rock** | `0.408` |
| 395 | Villa wunderbar | Irmin Schmidt | `krautrock, avant-garde` | **Rock** | `0.491` |
| 396 | L'Ultima Cena (Music from the Exhibition) | Maston | `` | **Other / Unclassified** | `0.0` |
| 397 | Svendsen, J.: Orchestral Music | Johan Svendsen | `` | **Other / Unclassified** | `0.0` |
| 398 | Wilds | Andy Shauf | `` | **Other / Unclassified** | `0.0` |
| 399 | Raw Honey | Drugdealer | `` | **Other / Unclassified** | `0.0` |
| 400 | When You Walk a Long Distance You Are Tired | Mothers | `` | **Other / Unclassified** | `0.0` |
| 401 | Adieux Au Dancefloor | Marie Davidson | `electroclash` | **Other / Unclassified** | `0.233` |
| 402 | The United States Of The Broken Hearted | Jeb Loy Nichols | `` | **Other / Unclassified** | `0.0` |
| 403 | Unusua | Toro y Moi | `chillwave` | **Other / Unclassified** | `0.345` |
| 404 | Peace Reign | Yukimi | `` | **Other / Unclassified** | `0.0` |
| 405 | The Cosmic Selector Vol. 1 | Lord Huron | `` | **Other / Unclassified** | `0.0` |
| 406 | Remixes Are Also Magic | John Grant | `` | **Other / Unclassified** | `0.0` |
| 407 | Mid Spiral | BADBADNOTGOOD | `` | **Other / Unclassified** | `0.0` |
| 408 | Family Of Aliens | Teleman | `` | **Other / Unclassified** | `0.0` |
| 409 | In Another Life | Sandro Perri | `` | **Other / Unclassified** | `0.0` |
| 410 | We Can Die Happy | Tennis | `` | **Other / Unclassified** | `0.0` |
| 411 | The Last Rotation Of Earth | BC Camplight | `` | **Other / Unclassified** | `0.0` |
| 412 | Feeling Good | Dorothy Ashby | `exotica` | **Other / Unclassified** | `0.297` |
| 413 | Bills & Aches & Blues EP2 (40 Years of 4AD) | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 414 | Prospect Of Skelmersdale | The Magnetic North | `` | **Other / Unclassified** | `0.0` |
| 415 | Still Living | Ganglians | `` | **Other / Unclassified** | `0.0` |
| 416 | Pacific Ocean Blue & Bambu - 2 CD Deluxe Legacy Edition | Dennis Wilson | `` | **Other / Unclassified** | `0.0` |
| 417 | REFRACTIONS | Cornelius | `shibuya-kei, plunderphonics` | **Other / Unclassified** | `0.344` |
| 418 | Pursuit of Ends | High Pulp | `jazz funk, jazz fusion, nu jazz` | **Jazz** | `0.7` |
| 419 | Texas Sun | Khruangbin | `neo-psychedelic` | **Rock** | `0.408` |
| 420 | SAVE YOURSELF | SBTRKT | `` | **Other / Unclassified** | `0.0` |
| 421 | Oh. What. Fun. (Original Motion Picture Soundtrack) | Oh. What. Fun. | `christmas` | **Other / Unclassified** | `0.221` |
| 422 | Good Remix/Hard Remix | Teleman | `` | **Other / Unclassified** | `0.0` |
| 423 | Darning Woman | Anastasia Coope | `` | **Other / Unclassified** | `0.0` |
| 424 | Ookii Gekkou | Vanishing Twin | `neo-psychedelic` | **Rock** | `0.408` |
| 425 | Aisles | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 426 | Tag Eins Tag Zwei | F.S.Blumm | `neoclassical, minimalism` | **Other / Unclassified** | `0.261` |
| 427 | Orange Wine | Okvsho | `jazz house, nu jazz, indie jazz` | **Jazz** | `0.688` |
| 428 | La Reproduction | Arnaud Fleurent-Didier | `` | **Other / Unclassified** | `0.0` |
| 429 | Happiness | DARGZ | `` | **Other / Unclassified** | `0.0` |
| 430 | Comme ça | Domenique Dumont | `` | **Other / Unclassified** | `0.0` |
| 431 | Spotify Live | BADBADNOTGOOD | `` | **Other / Unclassified** | `0.0` |
| 432 | Marshmallow | The Sweet Enoughs | `exotica` | **Other / Unclassified** | `0.297` |
| 433 | It Was the Moment | Michelle Gurevich | `slowcore` | **Other / Unclassified** | `0.29` |
| 434 | Grizzly Peak | The Dodos | `` | **Other / Unclassified** | `0.0` |
| 435 | The Tunnel and the Clearing | Colleen | `` | **Other / Unclassified** | `0.0` |
| 436 | Suppose | Blue House | `neo-psychedelic` | **Rock** | `0.408` |
| 437 | Spirit of the Golden Juice | F. J. McMahon | `` | **Other / Unclassified** | `0.0` |
| 438 | Fountain Of You | Peter Perrett | `` | **Other / Unclassified** | `0.0` |
| 439 | Soul Jazz Records Presents 100% Dynamite! Ska, Soul, Rocksteady and Funk in Jamaica | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 440 | Soul Jazz Records Presents Studio One Rocksteady 2: The Soul of Young Jamaica: Rocksteady, Soul and Early Reggae at Studio One | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 441 | Anagrams | Stephen Steinbrink | `` | **Other / Unclassified** | `0.0` |
| 442 | The King of Sudanese Jazz (Habibi Funk 013) | Sharhabil Ahmed | `` | **Other / Unclassified** | `0.0` |
| 443 | Above the Clouds | Resavoir | `` | **Other / Unclassified** | `0.0` |
| 444 | Prince of Tears | Baxter Dury | `` | **Other / Unclassified** | `0.0` |
| 445 | Frozen Flashes | Okvsho | `jazz house, nu jazz, indie jazz` | **Jazz** | `0.688` |
| 446 | Soul Jazz Records Presents HUSTLE! Reggae Disco - Kingston, London, New York | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 447 | All Over Me | Yukimi | `` | **Other / Unclassified** | `0.0` |
| 448 | The Hex | Richard Swift | `` | **Other / Unclassified** | `0.0` |
| 449 | Dear Scott | Michael Head & The Red Elastic Band | `` | **Other / Unclassified** | `0.0` |
| 450 | Dreamer+ | Sassy 009 | `` | **Other / Unclassified** | `0.0` |
| 451 | The Age Of Immunology | Vanishing Twin | `neo-psychedelic` | **Rock** | `0.408` |
| 452 | Ecstasy in the Shadow of Ecstasy | Michelle Gurevich | `slowcore` | **Other / Unclassified** | `0.29` |
| 453 | For You | Yukimi | `` | **Other / Unclassified** | `0.0` |
| 454 | Once Upon A Time... In Shropshire | Jerskin Fendrix | `score` | **Other / Unclassified** | `0.139` |
| 455 | Empty Seats | TOPS | `` | **Other / Unclassified** | `0.0` |
| 456 | Essam | Imarhan | `gnawa` | **Other / Unclassified** | `0.173` |
| 457 | Kablooey | Meric Long | `` | **Other / Unclassified** | `0.0` |
| 458 | Two Little Boys | The Last Poets | `spoken word` | **Other / Unclassified** | `0.226` |
| 459 | Country Agenda | Alex Bleeker & The Freaks | `` | **Other / Unclassified** | `0.0` |
| 460 | Party Girl | Michelle Gurevich | `slowcore` | **Other / Unclassified** | `0.29` |
| 461 | Tsu Gi Ne Pu | Asa-Chang & Junray | `shibuya-kei` | **Other / Unclassified** | `0.222` |
| 462 | Romantic Images | Molly Burch | `` | **Other / Unclassified** | `0.0` |
| 463 | Personal Record | Eleanor Friedberger | `` | **Other / Unclassified** | `0.0` |
| 464 | Soul Jazz Records Presents DANCEHALL: The Rise Of Jamaican Dancehall Culture | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 465 | Adagio | Σtella | `` | **Other / Unclassified** | `0.0` |
| 466 | Humanworld | Peter Perrett | `` | **Other / Unclassified** | `0.0` |
| 467 | Phonetics On and On | Horsegirl | `lo-fi indie` | **Pop** | `0.532` |
| 468 | Levitate | Idaho | `slowcore` | **Other / Unclassified** | `0.29` |
| 469 | Alluvium | C Duncan | `` | **Other / Unclassified** | `0.0` |
| 470 | Music from 'Likely Stories' | Jarvis Cocker | `` | **Other / Unclassified** | `0.0` |
| 471 | Transitions | SBTRKT | `` | **Other / Unclassified** | `0.0` |
| 472 | Lapse | Idaho | `slowcore` | **Other / Unclassified** | `0.29` |
| 473 | Eccentric Soul: The Outskirts Of Deep City | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 474 | Device Control EP | Wolfgang Tillmans | `` | **Other / Unclassified** | `0.0` |
| 475 | Gobstopper | Blue House | `neo-psychedelic` | **Rock** | `0.408` |
| 476 | Through | Carol Ades | `` | **Other / Unclassified** | `0.0` |
| 477 | How The West Was Won | Peter Perrett | `` | **Other / Unclassified** | `0.0` |
| 478 | Inside Out | Nilüfer Yanya | `` | **Other / Unclassified** | `0.0` |
| 479 | Selected Studies, Vol. 1 | Lloyd Cole | `` | **Other / Unclassified** | `0.0` |
| 480 | Dangerous Boys | Jeremy Jay | `` | **Other / Unclassified** | `0.0` |
| 481 | Nothing's Changed | Justus Proffit | `lo-fi indie` | **Pop** | `0.532` |
| 482 | In Piscina! | Vanishing Twin | `neo-psychedelic` | **Rock** | `0.408` |
| 483 | It's a Style Sport | Shabazz Palaces | `experimental hip hop, alternative hip hop` | **Hip-Hop** | `0.536` |
| 484 | Waterslide, Diving Board, Ladder To The Sky | Porridge Radio | `lo-fi indie` | **Pop** | `0.532` |
| 485 | Walt Wolfman | Richard Swift | `` | **Other / Unclassified** | `0.0` |
| 486 | Late Night Tales: Metronomy (Sampler) | Metronomy | `new rave, alternative dance` | **Reggae / Dub** | `0.406` |
| 487 | Goes Swimming | Moon Mullins | `` | **Other / Unclassified** | `0.0` |
| 488 | Wild Boy: The Lost Songs of Eden Ahbez | Eden Ahbez | `exotica, spoken word` | **Other / Unclassified** | `0.312` |
| 489 | Para Todos | Natalie Greffel | `` | **Other / Unclassified** | `0.0` |
| 490 | Bills & Aches & Blues EP1 (40 Years of 4AD) | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 491 | French Kiss | Chilly Gonzales | `neoclassical` | **Other / Unclassified** | `0.247` |
| 492 | We Fall Together | St Francis Hotel | `` | **Other / Unclassified** | `0.0` |
| 493 | Tumblers from the Vault | Syrinx | `krautrock` | **Other / Unclassified** | `0.336` |
| 494 | Soul Jazz Records Presents Soul of a Nation: Afro-Centric Visions in the Age of Black Power | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 495 | Swimming | Marigold Sun | `` | **Other / Unclassified** | `0.0` |
| 496 | Introduction to Escape-ism | Escape-ism | `` | **Other / Unclassified** | `0.0` |
| 497 | Jassbusters Two | Connan Mockasin | `` | **Other / Unclassified** | `0.0` |
| 498 | Paralelo | Pascal Comelade | `musique concrète` | **Jazz** | `0.354` |
| 499 | Can's Ege Bamyasi | Stephen Malkmus | `` | **Other / Unclassified** | `0.0` |
| 500 | Sweet Morning EP | Teleman | `` | **Other / Unclassified** | `0.0` |
| 501 | Dressed Up For The Let Down | Richard Swift | `` | **Other / Unclassified** | `0.0` |
| 502 | Gallop | Lena Platonos | `` | **Other / Unclassified** | `0.0` |
| 503 | Tableau | The Orielles | `` | **Other / Unclassified** | `0.0` |
| 504 | Hiding in Plain Sight | Drugdealer | `` | **Other / Unclassified** | `0.0` |
| 505 | Florida Water Blues | Twisted Teens | `` | **Other / Unclassified** | `0.0` |
| 506 | Polymood | L'Eclair | `` | **Other / Unclassified** | `0.0` |
| 507 | Forever Dolphin Love | Connan Mockasin | `` | **Other / Unclassified** | `0.0` |
| 508 | From Metropolis Studios | Kokoroko | `` | **Other / Unclassified** | `0.0` |
| 509 | Ethiopiques, vol. 21: Emahoy (Piano Solo) | Emahoy Tsege Mariam Gebru | `` | **Other / Unclassified** | `0.0` |
| 510 | K Bay | Matthew E. White | `` | **Other / Unclassified** | `0.0` |
| 511 | Heaven on the Faultline | Alex Bleeker | `` | **Other / Unclassified** | `0.0` |
| 512 | Two Intermezzos and a Waltz | Moon Mullins | `` | **Other / Unclassified** | `0.0` |
| 513 | A Place That Has No Memory of You | Laurent Dehors | `neoclassical` | **Other / Unclassified** | `0.247` |
| 514 | Hotel Paradiso | Moon Mullins | `` | **Other / Unclassified** | `0.0` |
| 515 | Texas Moon | Khruangbin | `neo-psychedelic` | **Rock** | `0.408` |
| 516 | Far From Born Again | Alex Cameron | `` | **Other / Unclassified** | `0.0` |
| 517 | Solo Piano III | Chilly Gonzales | `neoclassical` | **Other / Unclassified** | `0.247` |
| 518 | Some Other Ones | Mac DeMarco | `indie, lo-fi indie` | **Pop** | `0.622` |
| 519 | Rennen | SOHN | `` | **Other / Unclassified** | `0.0` |
| 520 | Eat Your Own Ears Recordings EP 1 / 2 | Eat Your Own Ears Recordings | `` | **Other / Unclassified** | `0.0` |
| 521 | Only You Left | The Orielles | `` | **Other / Unclassified** | `0.0` |
| 522 | Hurtsville | Jack Ladder | `` | **Other / Unclassified** | `0.0` |
| 523 | Soul Jazz Records Presents VENEZUELA 70: Cosmic Visions Of A Latin American Earth - Venezuelan Experimental Rock In The 1970s | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 524 | Music for Maison d'en face | La marche bleue | `` | **Other / Unclassified** | `0.0` |
| 525 | Other Death | Sean Nicholas Savage | `` | **Other / Unclassified** | `0.0` |
| 526 | Petunia | Tonstartssbandht | `neo-psychedelic` | **Rock** | `0.408` |
| 527 | Souvenir | Maston | `` | **Other / Unclassified** | `0.0` |
| 528 | Daybreak | Sven Wunder | `neo-psychedelic` | **Rock** | `0.408` |
| 529 | Musique Sans Paroles | Pierre Rousseau | `` | **Other / Unclassified** | `0.0` |
| 530 | Late Night Tales: Nouvelle Vague (Sampler) | Nouvelle Vague | `lounge` | **Other / Unclassified** | `0.261` |
| 531 | African Electronic Music 1975 - 1982 | Francis Bebey | `bikutsi` | **Other / Unclassified** | `0.143` |
| 532 | Psychedelic Sanza | Francis Bebey | `bikutsi` | **Other / Unclassified** | `0.143` |
| 533 | Something Like A War | Kindness | `` | **Other / Unclassified** | `0.0` |
| 534 | Shortly After Takeoff | BC Camplight | `` | **Other / Unclassified** | `0.0` |
| 535 | Live at Electric Lady | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 536 | Renegade Breakdown | Marie Davidson | `electroclash` | **Other / Unclassified** | `0.233` |
| 537 | Fleuves de l'Âme | Houeida Hedfi | `` | **Other / Unclassified** | `0.0` |
| 538 | Summer Quarter | Madeline Kenney | `` | **Other / Unclassified** | `0.0` |
| 539 | Paint Your Wagon Soundtrack | The Paul Masters Orchestra | `` | **Other / Unclassified** | `0.0` |
| 540 | Soul Jazz Records Presents New Orleans Soul: The Original Sound Of New Orleans Soul 1960-76 | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 541 | Glass Flowers | Elysian Spring | `` | **Other / Unclassified** | `0.0` |
| 542 | For the Sake of Bethel Woods | Midlake | `` | **Other / Unclassified** | `0.0` |
| 543 | Yume | Yukimi | `` | **Other / Unclassified** | `0.0` |
| 544 | 10 Miles to Tilden | Moon Mullins | `` | **Other / Unclassified** | `0.0` |
| 545 | Anthology Soundtrack 1,2 & 3 | Irmin Schmidt | `krautrock, avant-garde` | **Rock** | `0.491` |
| 546 | The Devil Laughs | Stuart Moxham | `` | **Other / Unclassified** | `0.0` |
| 547 | UP | Max Pope | `` | **Other / Unclassified** | `0.0` |
| 548 | Balloon Maker | Midlake | `` | **Other / Unclassified** | `0.0` |
| 549 | WKWP | WKWP | `` | **Other / Unclassified** | `0.0` |
| 550 | Buzzz | Tipsy | `` | **Other / Unclassified** | `0.0` |
| 551 | Infinite Summer | NZCA LINES | `chillwave` | **Other / Unclassified** | `0.345` |
| 552 | Eat Your Own Ears Recordings EP 1 | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 553 | Falling Out | Otzeki | `` | **Other / Unclassified** | `0.0` |
| 554 | Eden's Island (Remastered) | Eden Ahbez | `exotica, spoken word` | **Other / Unclassified** | `0.312` |
| 555 | Flat White Moon | Field Music | `` | **Other / Unclassified** | `0.0` |
| 556 | Certainty Waves | The Dodos | `` | **Other / Unclassified** | `0.0` |
| 557 | Carré noir sur fond noir | Pascal Comelade | `musique concrète` | **Jazz** | `0.354` |
| 558 | Fireflies | Devendra Banhart | `` | **Other / Unclassified** | `0.0` |
| 559 | The Visitor | Kadhja Bonet | `` | **Other / Unclassified** | `0.0` |
| 560 | Bunny | Charles Wilp | `` | **Other / Unclassified** | `0.0` |
| 561 | With You Every Night | Ariel Pink | `neo-psychedelic` | **Rock** | `0.408` |
| 562 | The Pet Parade | Fruit Bats | `` | **Other / Unclassified** | `0.0` |
| 563 | Half Way Home | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 564 | Room 29 | Chilly Gonzales | `neoclassical` | **Other / Unclassified** | `0.247` |
| 565 | Soul Jazz Records Presents New Orleans Funk 4: Voodoo Fire In New Orleans 1951-75 | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 566 | Juniata | Becca Mancari | `` | **Other / Unclassified** | `0.0` |
| 567 | Late to Set | Alex Cameron | `` | **Other / Unclassified** | `0.0` |
| 568 | Barbarians | Richard Davies | `` | **Other / Unclassified** | `0.0` |
| 569 | Fünf EP | Teleman | `` | **Other / Unclassified** | `0.0` |
| 570 | Filmmusik Anthology 4 & 5 | Irmin Schmidt | `krautrock, avant-garde` | **Rock** | `0.491` |
| 571 | 12 Blown Tires | Tennis | `` | **Other / Unclassified** | `0.0` |
| 572 | Pelota | Khruangbin | `neo-psychedelic` | **Rock** | `0.408` |
| 573 | Other People's Pieces | Chilly Gonzales | `neoclassical` | **Other / Unclassified** | `0.247` |
| 574 | NZCA/LINES (Spotify Deluxe Edition) | NZCA LINES | `` | **Other / Unclassified** | `0.0` |
| 575 | Jogos de Armar: Faça Você Mesmo | Tom Zé | `mpb` | **Other / Unclassified** | `0.203` |
| 576 | Schubert: Winterreise | Franz Schubert | `chamber music, classical, classical piano` | **Classical** | `0.758` |
| 577 | Boniface | Boniface | `` | **Other / Unclassified** | `0.0` |
| 578 | Bedouine (Deluxe) | Bedouine | `` | **Other / Unclassified** | `0.0` |
| 579 | 11 | SAULT | `` | **Other / Unclassified** | `0.0` |
| 580 | Strange Cacti | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 581 | Living Thing | Peter Bjorn and John | `indie` | **Pop** | `0.591` |
| 582 | Annihilation | TOPS | `` | **Other / Unclassified** | `0.0` |
| 583 | The Roches | The Roches | `` | **Other / Unclassified** | `0.0` |
| 584 | City Lights | The WAEVE | `` | **Other / Unclassified** | `0.0` |
| 585 | Badge Époque Ensemble | Badge Époque Ensemble | `` | **Other / Unclassified** | `0.0` |
| 586 | Dita Von Teese | Dita Von Teese | `italo disco` | **Latin / World** | `0.381` |
| 587 | A Private Road | Laura Groves | `` | **Other / Unclassified** | `0.0` |
| 588 | Late Night Tales: Khruangbin | Khruangbin | `neo-psychedelic` | **Rock** | `0.408` |
| 589 | Late Night Tales Presents After Dark: Nocturne | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 590 | For the Birds: The Birdsong Project, Vol. I | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 591 | 10 | SAULT | `` | **Other / Unclassified** | `0.0` |
| 592 | Fear Of Death | Tim Heidecker | `` | **Other / Unclassified** | `0.0` |
| 593 | Chapter 1 | SAULT | `` | **Other / Unclassified** | `0.0` |
| 594 | Jenius | Paul Heaton | `` | **Other / Unclassified** | `0.0` |
| 595 | Utopia Defeated | D.D Dumbo | `` | **Other / Unclassified** | `0.0` |
| 596 | Boy from Michigan | John Grant | `` | **Other / Unclassified** | `0.0` |
| 597 | The Phantoms & The Archetypes | Paul Quinn & The Independent Group | `` | **Other / Unclassified** | `0.0` |
| 598 | Bubblegum | Biig Piig | `` | **Other / Unclassified** | `0.0` |
| 599 | Kelly Lee Owens | Kelly Lee Owens | `` | **Other / Unclassified** | `0.0` |
| 600 | Marie Davidson | Marie Davidson | `electroclash` | **Other / Unclassified** | `0.233` |
| 601 | The Versatile Henry Mancini And His Orchestra | Henry Mancini | `exotica, adult standards, easy listening` | **Latin / World** | `0.486` |
| 602 | Solo Piano | Chilly Gonzales | `` | **Other / Unclassified** | `0.0` |
| 603 | Late Night Tales Presents: After Dark - Vespertine | Bill Brewster | `` | **Other / Unclassified** | `0.0` |
| 604 | My Light, My Destroyer | Cassandra Jenkins | `` | **Other / Unclassified** | `0.0` |
| 605 | El Baile Alemán | Señor Coconut | `cha cha cha, exotica` | **Latin / World** | `0.351` |
| 606 | Disco Volador | The Orielles | `` | **Other / Unclassified** | `0.0` |
| 607 | Face Down In The Garden | Tennis | `` | **Other / Unclassified** | `0.0` |
| 608 | Park | PARK | `` | **Other / Unclassified** | `0.0` |
| 609 | King Krule | King Krule | `` | **Other / Unclassified** | `0.0` |
| 610 | Loophole | Michael Head & The Red Elastic Band | `` | **Other / Unclassified** | `0.0` |
| 611 | SAYA | Saya Gray | `` | **Other / Unclassified** | `0.0` |
| 612 | Chairlift at 6:15 | Chairlift | `` | **Other / Unclassified** | `0.0` |
| 613 | Reset Mariachi EP | Panda Bear | `neo-psychedelic` | **Rock** | `0.408` |
| 614 | Alex Bleeker and The Freaks | Alex Bleeker & The Freaks | `` | **Other / Unclassified** | `0.0` |
| 615 | Ow ∞ | Sylvan Esso | `` | **Other / Unclassified** | `0.0` |
| 616 | Darker Days | Peter Bjorn and John | `indie` | **Pop** | `0.591` |
| 617 | The Singing Hatchet | Radar Brothers | `slowcore` | **Other / Unclassified** | `0.29` |
| 618 | Hovvdy | Hovvdy | `lo-fi indie` | **Pop** | `0.532` |
| 619 | Blossoms | Blossoms | `indie` | **Pop** | `0.591` |
| 620 | i don’t know who needs to hear this... | Tomberlin | `` | **Other / Unclassified** | `0.0` |
| 621 | Anthem +3 | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 622 | Connan Mockasin as Mr Bostyn | Connan Mockasin | `` | **Other / Unclassified** | `0.0` |
| 623 | The Old Law | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 624 | Blue Maqams | Anouar Brahem | `` | **Other / Unclassified** | `0.0` |
| 625 | Jumping the Shark | Alex Cameron | `` | **Other / Unclassified** | `0.0` |
| 626 | yaeji | Yaeji | `` | **Other / Unclassified** | `0.0` |
| 627 | Emilia Pérez (Original Motion Picture Soundtrack) | Clément Ducol | `` | **Other / Unclassified** | `0.0` |
| 628 | Weird Little Birthday | Happyness | `lo-fi indie` | **Pop** | `0.532` |
| 629 | Late Night Tales Presents Version Excursion Selected by Don Letts | Don Letts | `` | **Other / Unclassified** | `0.0` |
| 630 | A Peace of Us | Dean & Britta | `` | **Other / Unclassified** | `0.0` |
| 631 | Kiss Each Other Clean | Iron & Wine | `` | **Other / Unclassified** | `0.0` |
| 632 | Acts of Faith | SAULT | `` | **Other / Unclassified** | `0.0` |
| 633 | Rise Up 20 | Phoenix | `` | **Other / Unclassified** | `0.0` |
| 634 | 2 | Foxwarren | `` | **Other / Unclassified** | `0.0` |
| 635 | Everyone's Getting Involved: A Tribute to Talking Heads' Stop Making Sense | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 636 | The Solution Is Restless | Joan As Police Woman | `` | **Other / Unclassified** | `0.0` |
| 637 | In Quiet Moments | Lost Horizons | `` | **Other / Unclassified** | `0.0` |
| 638 | Florist | Florist | `` | **Other / Unclassified** | `0.0` |
| 639 | Tracyanne & Danny | Tracyanne & Danny | `` | **Other / Unclassified** | `0.0` |
| 640 | PAINT | PAINT | `neo-psychedelic` | **Rock** | `0.408` |
| 641 | Dead Dog's Eyeball - Songs of Daniel Johnston | Kathy McCarty | `` | **Other / Unclassified** | `0.0` |
| 642 | Don't Let the Kids Win | Julia Jacklin | `` | **Other / Unclassified** | `0.0` |
| 643 | Owiny Sigoma Band | Owiny Sigoma Band | `` | **Other / Unclassified** | `0.0` |
| 644 | People On Sunday | Domenique Dumont | `` | **Other / Unclassified** | `0.0` |
| 645 | Green To Gold | The Antlers | `` | **Other / Unclassified** | `0.0` |
| 646 | Pleasure | Feist | `` | **Other / Unclassified** | `0.0` |
| 647 | Movie | Holger Czukay | `krautrock` | **Other / Unclassified** | `0.336` |
| 648 | Impossible Spaces | Sandro Perri | `` | **Other / Unclassified** | `0.0` |
| 649 | April | Sun Kil Moon | `slowcore, southern gothic` | **Metal** | `0.423` |
| 650 | Mortal Primetime | Sunflower Bean | `` | **Other / Unclassified** | `0.0` |
| 651 | Distant Sky (Live in Copenhagen) | Nick Cave & The Bad Seeds | `` | **Other / Unclassified** | `0.0` |
| 652 | Mordechai | Khruangbin | `neo-psychedelic` | **Rock** | `0.408` |
| 653 | This Could Be Texas | English Teacher | `` | **Other / Unclassified** | `0.0` |
| 654 | Nebraska | Bruce Springsteen | `` | **Other / Unclassified** | `0.0` |
| 655 | CARNAGE | Nick Cave | `` | **Other / Unclassified** | `0.0` |
| 656 | Last of the Country Gentlemen | Josh T. Pearson | `` | **Other / Unclassified** | `0.0` |
| 657 | Mama, You Can Bet! | Jyoti | `` | **Other / Unclassified** | `0.0` |
| 658 | Stranger in the Alps | Phoebe Bridgers | `` | **Other / Unclassified** | `0.0` |
| 659 | Lush | Snail Mail | `indie` | **Pop** | `0.591` |
| 660 | Health | C Duncan | `` | **Other / Unclassified** | `0.0` |
| 661 | Playing Robots Into Heaven | James Blake | `` | **Other / Unclassified** | `0.0` |
| 662 | Underneath The Pine | Toro y Moi | `chillwave` | **Other / Unclassified** | `0.345` |
| 663 | Forever Is A Feeling | Lucy Dacus | `` | **Other / Unclassified** | `0.0` |
| 664 | Boo Boo | Toro y Moi | `chillwave` | **Other / Unclassified** | `0.345` |
| 665 | Third Eye Blind | Third Eye Blind | `` | **Other / Unclassified** | `0.0` |
| 666 | Come To My Garden | Minnie Riperton | `` | **Other / Unclassified** | `0.0` |
| 667 | Picture You Staring | TOPS | `` | **Other / Unclassified** | `0.0` |
| 668 | Solo Piano II | Chilly Gonzales | `neoclassical` | **Other / Unclassified** | `0.247` |
| 669 | Good Lies | Overmono | `uk garage, breakbeat` | **Electronic** | `0.379` |
| 670 | Up | R.E.M. | `jangle pop, alternative rock, rock` | **Rock** | `0.621` |
| 671 | awE naturalE | THEESatisfaction | `` | **Other / Unclassified** | `0.0` |
| 672 | Greetings from Asbury Park, N.J. | Bruce Springsteen | `` | **Other / Unclassified** | `0.0` |
| 673 | Space Heavy | King Krule | `` | **Other / Unclassified** | `0.0` |
| 674 | EarthEE | THEESatisfaction | `` | **Other / Unclassified** | `0.0` |
| 675 | Silver & Gold | Sufjan Stevens | `` | **Other / Unclassified** | `0.0` |
| 676 | Individ | The Dodos | `` | **Other / Unclassified** | `0.0` |
| 677 | Nation Shall Speak Unto Nation | Edwyn Collins | `britpop` | **Pop** | `0.359` |
| 678 | Pollen | Tennis | `` | **Other / Unclassified** | `0.0` |
| 679 | Ti Amo | Phoenix | `indie` | **Pop** | `0.591` |
| 680 | Nine | SAULT | `` | **Other / Unclassified** | `0.0` |
| 681 | Distracted | Thundercat | `` | **Other / Unclassified** | `0.0` |
| 682 | EURO-COUNTRY | CMAT | `` | **Other / Unclassified** | `0.0` |
| 683 | A LA SALA | Khruangbin | `neo-psychedelic` | **Rock** | `0.408` |
| 684 | Laurel Hell | Mitski | `` | **Other / Unclassified** | `0.0` |
| 685 | Tracey Denim | bar italia | `lo-fi indie` | **Pop** | `0.532` |
| 686 | Love Is Magic | John Grant | `` | **Other / Unclassified** | `0.0` |
| 687 | The Slow Rush | Tame Impala | `neo-psychedelic, indie` | **Rock** | `0.597` |
| 688 | Sour Soul (Instrumentals) | BADBADNOTGOOD | `` | **Other / Unclassified** | `0.0` |
| 689 | Silver Dollar Moment | The Orielles | `` | **Other / Unclassified** | `0.0` |
| 690 | I've Been Trying To Tell You | Saint Etienne | `madchester, britpop, alternative dance` | **Pop** | `0.451` |
| 691 | God's Favorite Customer | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 692 | Here Comes The Cowboy | Mac DeMarco | `indie, lo-fi indie` | **Pop** | `0.622` |
| 693 | Soft Sounds from Another Planet | Japanese Breakfast | `` | **Other / Unclassified** | `0.0` |
| 694 | Talk Memory | BADBADNOTGOOD | `` | **Other / Unclassified** | `0.0` |
| 695 | The Far Field | Future Islands | `` | **Other / Unclassified** | `0.0` |
| 696 | We've Been Going About This All Wrong | Sharon Van Etten | `` | **Other / Unclassified** | `0.0` |
| 697 | Familiars | The Antlers | `` | **Other / Unclassified** | `0.0` |
| 698 | The Party | Andy Shauf | `` | **Other / Unclassified** | `0.0` |
| 699 | Yours Conditionally | Tennis | `` | **Other / Unclassified** | `0.0` |
| 700 | Myopia | Agnes Obel | `` | **Other / Unclassified** | `0.0` |
| 701 | Hot Dreams | Timber Timbre | `southern gothic` | **Latin / World** | `0.371` |
| 702 | Blood | Rhye | `` | **Other / Unclassified** | `0.0` |
| 703 | Autofiction | Suede | `britpop, madchester` | **Pop** | `0.362` |
| 704 | MERCY | John Cale | `` | **Other / Unclassified** | `0.0` |
| 705 | It Is What It Is | Thundercat | `` | **Other / Unclassified** | `0.0` |
| 706 | Making a New World | Field Music | `` | **Other / Unclassified** | `0.0` |
| 707 | Moth | Chairlift | `` | **Other / Unclassified** | `0.0` |
| 708 | Phases | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 709 | Afrique Victime | Mdou Moctar | `gnawa` | **Other / Unclassified** | `0.173` |
| 710 | Pool | Porches | `` | **Other / Unclassified** | `0.0` |
| 711 | First Flower | Molly Burch | `` | **Other / Unclassified** | `0.0` |
| 712 | Are We There | Sharon Van Etten | `` | **Other / Unclassified** | `0.0` |
| 713 | Animal | LUMP | `` | **Other / Unclassified** | `0.0` |
| 714 | Blue Banisters | Lana Del Rey | `` | **Other / Unclassified** | `0.0` |
| 715 | Untitled (Rise) | SAULT | `` | **Other / Unclassified** | `0.0` |
| 716 | Fuse | Everything But The Girl | `` | **Other / Unclassified** | `0.0` |
| 717 | The Golden Age | American Music Club | `slowcore` | **Other / Unclassified** | `0.29` |
| 718 | Untitled (Black Is) | SAULT | `` | **Other / Unclassified** | `0.0` |
| 719 | What's Tonight to Eternity | Cindy Lee | `` | **Other / Unclassified** | `0.0` |
| 720 | B.E.D | Baxter Dury | `` | **Other / Unclassified** | `0.0` |
| 721 | Dunya | Mustafa | `` | **Other / Unclassified** | `0.0` |
| 722 | Space Is Only Noise | Nicolas Jaar | `` | **Other / Unclassified** | `0.0` |
| 723 | Guitar | Mac DeMarco | `indie, lo-fi indie` | **Pop** | `0.622` |
| 724 | One Wayne G | Mac DeMarco | `indie, lo-fi indie` | **Pop** | `0.622` |
| 725 | We Will Always Love You | The Avalanches | `plunderphonics` | **Reggae / Dub** | `0.389` |
| 726 | Overgrown | James Blake | `` | **Other / Unclassified** | `0.0` |
| 727 | Forced Witness | Alex Cameron | `` | **Other / Unclassified** | `0.0` |
| 728 | Gold Past Life | Fruit Bats | `` | **Other / Unclassified** | `0.0` |
| 729 | Like a Baby | Jerry Paper | `` | **Other / Unclassified** | `0.0` |
| 730 | Mystic Familiar | Dan Deacon | `` | **Other / Unclassified** | `0.0` |
| 731 | Norm | Andy Shauf | `` | **Other / Unclassified** | `0.0` |
| 732 | Wild God | Nick Cave & The Bad Seeds | `` | **Other / Unclassified** | `0.0` |
| 733 | The English Riviera | Metronomy | `` | **Other / Unclassified** | `0.0` |
| 734 | Heaven To A Tortured Mind | Yves Tumor | `` | **Other / Unclassified** | `0.0` |
| 735 | Isles | BICEP | `` | **Other / Unclassified** | `0.0` |
| 736 | Be the Cowboy | Mitski | `` | **Other / Unclassified** | `0.0` |
| 737 | The Trials of Van Occupanther | Midlake | `` | **Other / Unclassified** | `0.0` |
| 738 | color theory | Soccer Mommy | `indie` | **Pop** | `0.591` |
| 739 | Broadcast And The Focus Group Investigate Witch Cults Of The Radio Age | Broadcast And The Focus Group | `` | **Other / Unclassified** | `0.0` |
| 740 | Aventine | Agnes Obel | `` | **Other / Unclassified** | `0.0` |
| 741 | The Greatest Part | Becca Mancari | `` | **Other / Unclassified** | `0.0` |
| 742 | III | BADBADNOTGOOD | `` | **Other / Unclassified** | `0.0` |
| 743 | In Waves | Jamie xx | `` | **Other / Unclassified** | `0.0` |
| 744 | TO LOVE IS TO LIVE | Jehnny Beth | `` | **Other / Unclassified** | `0.0` |
| 745 | Materia | Julia Holter | `` | **Other / Unclassified** | `0.0` |
| 746 | McCartney II | Paul McCartney | `` | **Other / Unclassified** | `0.0` |
| 747 | Miami Memory | Alex Cameron | `` | **Other / Unclassified** | `0.0` |
| 748 | Bright Future | Adrianne Lenker | `` | **Other / Unclassified** | `0.0` |
| 749 | Prelude to Ecstasy | The Last Dinner Party | `` | **Other / Unclassified** | `0.0` |
| 750 | Lost Weekend | Phoebe Bridgers | `` | **Other / Unclassified** | `0.0` |
| 751 | abysskiss | Adrianne Lenker | `` | **Other / Unclassified** | `0.0` |
| 752 | Light Upon the Lake | Whitney | `` | **Other / Unclassified** | `0.0` |
| 753 | MAHAL | Toro y Moi | `chillwave` | **Other / Unclassified** | `0.345` |
| 754 | Eucalyptus | Avey Tare | `neo-psychedelic` | **Rock** | `0.408` |
| 755 | Falling Off The Lavender Bridge | Lightspeed Champion | `` | **Other / Unclassified** | `0.0` |
| 756 | Ali | Vieux Farka Touré | `` | **Other / Unclassified** | `0.0` |
| 757 | Details | Frou Frou | `` | **Other / Unclassified** | `0.0` |
| 758 | Leonard Cohen: I'm Your Man | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 759 | More | Pulp | `britpop` | **Pop** | `0.359` |
| 760 | CHANSONS d’ENNUI TIP-TOP | Jarvis Cocker | `` | **Other / Unclassified** | `0.0` |
| 761 | If I don't make it, I love u | Still House Plants | `` | **Other / Unclassified** | `0.0` |
| 762 | The Night Chancers | Baxter Dury | `` | **Other / Unclassified** | `0.0` |
| 763 | moogmemory | Matthew Bourne | `neoclassical` | **Other / Unclassified** | `0.247` |
| 764 | American Head | The Flaming Lips | `neo-psychedelic` | **Rock** | `0.408` |
| 765 | New View | Eleanor Friedberger | `` | **Other / Unclassified** | `0.0` |
| 766 | Plumb | Field Music | `` | **Other / Unclassified** | `0.0` |
| 767 | I Feel Alive | TOPS | `` | **Other / Unclassified** | `0.0` |
| 768 | Ghosteen | Nick Cave & The Bad Seeds | `` | **Other / Unclassified** | `0.0` |
| 769 | Trying Times | James Blake | `` | **Other / Unclassified** | `0.0` |
| 770 | Two Hands | Big Thief | `` | **Other / Unclassified** | `0.0` |
| 771 | Man Alive! | King Krule | `` | **Other / Unclassified** | `0.0` |
| 772 | Five Easy Hot Dogs | Mac DeMarco | `indie, lo-fi indie` | **Pop** | `0.622` |
| 773 | Saturdays = Youth | M83 | `` | **Other / Unclassified** | `0.0` |
| 774 | Mug Museum | Cate Le Bon | `` | **Other / Unclassified** | `0.0` |
| 775 | In the End It Always Does | The Japanese House | `` | **Other / Unclassified** | `0.0` |
| 776 | Still Life | Kevin Morby | `` | **Other / Unclassified** | `0.0` |
| 777 | Fantasma (Remastered) | Cornelius | `shibuya-kei, plunderphonics` | **Other / Unclassified** | `0.344` |
| 778 | Air | SAULT | `` | **Other / Unclassified** | `0.0` |
| 779 | Childqueen | Kadhja Bonet | `` | **Other / Unclassified** | `0.0` |
| 780 | Planetarium | James McAlister | `` | **Other / Unclassified** | `0.0` |
| 781 | City Music | Kevin Morby | `` | **Other / Unclassified** | `0.0` |
| 782 | With A Hammer | Yaeji | `` | **Other / Unclassified** | `0.0` |
| 783 | Mahashmashana | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 784 | La question | Françoise Hardy | `chanson, french pop, variété française, french jazz` | **Jazz** | `0.519` |
| 785 | An Overview on Phenomenal Nature | Cassandra Jenkins | `` | **Other / Unclassified** | `0.0` |
| 786 | Remind Me Tomorrow | Sharon Van Etten | `` | **Other / Unclassified** | `0.0` |
| 787 | Whole New Mess | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 788 | IV | BADBADNOTGOOD | `` | **Other / Unclassified** | `0.0` |
| 789 | american dream | LCD Soundsystem | `alternative dance, new rave` | **Reggae / Dub** | `0.423` |
| 790 | Assume Form | James Blake | `` | **Other / Unclassified** | `0.0` |
| 791 | Dragon New Warm Mountain I Believe In You | Big Thief | `` | **Other / Unclassified** | `0.0` |
| 792 | This Is A Photograph | Kevin Morby | `` | **Other / Unclassified** | `0.0` |
| 793 | The WAEVE | The WAEVE | `` | **Other / Unclassified** | `0.0` |
| 794 | The Atlantic Ocean | Richard Swift | `` | **Other / Unclassified** | `0.0` |
| 795 | Wildflower | The Avalanches | `plunderphonics` | **Reggae / Dub** | `0.389` |
| 796 | Clean | Soccer Mommy | `indie` | **Pop** | `0.591` |
| 797 | My Method Actor | Nilüfer Yanya | `` | **Other / Unclassified** | `0.0` |
| 798 | No Burden | Lucy Dacus | `` | **Other / Unclassified** | `0.0` |
| 799 | Capacity | Big Thief | `` | **Other / Unclassified** | `0.0` |
| 800 | Outer Peace | Toro y Moi | `chillwave` | **Other / Unclassified** | `0.345` |
| 801 | Strange Trails | Lord Huron | `` | **Other / Unclassified** | `0.0` |
| 802 | Punching the Clown | Lambchop | `` | **Other / Unclassified** | `0.0` |
| 803 | Gentle Spirit | Jonathan Wilson | `` | **Other / Unclassified** | `0.0` |
| 804 | Reset (Expanded Edition) | Panda Bear | `neo-psychedelic` | **Rock** | `0.408` |
| 805 | Dreams | The Whitest Boy Alive | `` | **Other / Unclassified** | `0.0` |
| 806 | Ricochet | Snail Mail | `indie` | **Pop** | `0.591` |
| 807 | Mingus | Joni Mitchell | `` | **Other / Unclassified** | `0.0` |
| 808 | Beyond the Pale | Jarvis Cocker | `` | **Other / Unclassified** | `0.0` |
| 809 | Long Lost | Lord Huron | `` | **Other / Unclassified** | `0.0` |
| 810 | The Sunset Violent | Mount Kimbie | `` | **Other / Unclassified** | `0.0` |
| 811 | Metronomy Forever | Metronomy | `new rave, alternative dance` | **Reggae / Dub** | `0.406` |
| 812 | Nobody Loves You More | Kim Deal | `` | **Other / Unclassified** | `0.0` |
| 813 | In Case We Die | Architecture In Helsinki | `` | **Other / Unclassified** | `0.0` |
| 814 | V | Unknown Mortal Orchestra | `neo-psychedelic` | **Rock** | `0.408` |
| 815 | I Thought I Was Better Than You | Baxter Dury | `` | **Other / Unclassified** | `0.0` |
| 816 | The Neon Skyline | Andy Shauf | `` | **Other / Unclassified** | `0.0` |
| 817 | Sugar at the Gate | TOPS | `` | **Other / Unclassified** | `0.0` |
| 818 | The Nearer The Fountain, More Pure The Stream Flows | Damon Albarn | `` | **Other / Unclassified** | `0.0` |
| 819 | Badbea | Edwyn Collins | `britpop` | **Pop** | `0.359` |
| 820 | The Midnight Sun | C Duncan | `` | **Other / Unclassified** | `0.0` |
| 821 | The Straight Hits! | Josh T. Pearson | `` | **Other / Unclassified** | `0.0` |
| 822 | Sincerely, Future Pollution | Timber Timbre | `southern gothic` | **Latin / World** | `0.371` |
| 823 | Commontime | Field Music | `` | **Other / Unclassified** | `0.0` |
| 824 | Iechyd Da | Bill Ryder-Jones | `` | **Other / Unclassified** | `0.0` |
| 825 | Rest | Charlotte Gainsbourg | `` | **Other / Unclassified** | `0.0` |
| 826 | Sometimes I Might Be Introvert | Little Simz | `` | **Other / Unclassified** | `0.0` |
| 827 | Oh My God | Kevin Morby | `` | **Other / Unclassified** | `0.0` |
| 828 | SAWAYAMA | Rina Sawayama | `` | **Other / Unclassified** | `0.0` |
| 829 | Mutable Set | Blake Mills | `` | **Other / Unclassified** | `0.0` |
| 830 | PAINLESS | Nilüfer Yanya | `` | **Other / Unclassified** | `0.0` |
| 831 | God Save The Animals | Alex G | `` | **Other / Unclassified** | `0.0` |
| 832 | Cows on Hourglass Pond | Avey Tare | `neo-psychedelic` | **Rock** | `0.408` |
| 833 | Love What Survives | Mount Kimbie | `` | **Other / Unclassified** | `0.0` |
| 834 | I See You | The xx | `` | **Other / Unclassified** | `0.0` |
| 835 | Panda Bear Meets The Grim Reaper | Panda Bear | `neo-psychedelic` | **Rock** | `0.408` |
| 836 | House of Sugar | Alex G | `` | **Other / Unclassified** | `0.0` |
| 837 | Topical Dancer | Charlotte Adigéry | `` | **Other / Unclassified** | `0.0` |
| 838 | In Colour | Jamie xx | `` | **Other / Unclassified** | `0.0` |
| 839 | Late Night Tales: Agnes Obel | Agnes Obel | `` | **Other / Unclassified** | `0.0` |
| 840 | Oxy Music | Alex Cameron | `` | **Other / Unclassified** | `0.0` |
| 841 | Mid Air | Romy | `` | **Other / Unclassified** | `0.0` |
| 842 | Afternoon X | Vanishing Twin | `neo-psychedelic` | **Rock** | `0.408` |
| 843 | Every Bad | Porridge Radio | `lo-fi indie` | **Pop** | `0.532` |
| 844 | Chaos For The Fly | Grian Chatten | `` | **Other / Unclassified** | `0.0` |
| 845 | Virtual Dreams II - Ambient Explorations In The House & Techno Age, Japan 1993-1999 | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 846 | Small World | Metronomy | `new rave, alternative dance` | **Reggae / Dub** | `0.406` |
| 847 | Cold Spring Fault Less Youth | Mount Kimbie | `` | **Other / Unclassified** | `0.0` |
| 848 | The Smell of Our Own (20th Anniversary Edition) | The Hidden Cameras | `queercore` | **Punk / Alternative** | `0.435` |
| 849 | Con Todo El Mundo | Khruangbin | `neo-psychedelic` | **Rock** | `0.408` |
| 850 | Late Night Tales: BADBADNOTGOOD | BADBADNOTGOOD | `` | **Other / Unclassified** | `0.0` |
| 851 | All This I Do For Glory | Colin Stetson | `` | **Other / Unclassified** | `0.0` |
| 852 | Chemtrails Over The Country Club | Lana Del Rey | `` | **Other / Unclassified** | `0.0` |
| 853 | Out Of The Game | Rufus Wainwright | `` | **Other / Unclassified** | `0.0` |
| 854 | The Bearer of Bad News | Andy Shauf | `` | **Other / Unclassified** | `0.0` |
| 855 | Lust For Life | Lana Del Rey | `` | **Other / Unclassified** | `0.0` |
| 856 | Chloë and the Next 20th Century | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 857 | Gorgeous George | Edwyn Collins | `britpop` | **Pop** | `0.359` |
| 858 | All Mirrors | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 859 | Summer 08 | Metronomy | `new rave, alternative dance` | **Reggae / Dub** | `0.406` |
| 860 | Montauk Variations | Matthew Bourne | `` | **Other / Unclassified** | `0.0` |
| 861 | MY WOMAN | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 862 | Sharon Van Etten & The Attachment Theory | Sharon Van Etten | `` | **Other / Unclassified** | `0.0` |
| 863 | Délivrance | A Hawk And A Hacksaw | `` | **Other / Unclassified** | `0.0` |
| 864 | Valentine | Snail Mail | `indie` | **Pop** | `0.591` |
| 865 | Pure Comedy | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 866 | Mother Earth's Plantasia | Mort Garson | `` | **Other / Unclassified** | `0.0` |
| 867 | From Kinshasa | Mbongwana Star | `` | **Other / Unclassified** | `0.0` |
| 868 | CHAI | CHAI | `` | **Other / Unclassified** | `0.0` |
| 869 | Burn Your Fire For No Witness (Deluxe Edition) | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 870 | Buoys | Panda Bear | `neo-psychedelic` | **Rock** | `0.408` |
| 871 | RAM | Paul McCartney | `` | **Other / Unclassified** | `0.0` |
| 872 | Drunk | Thundercat | `` | **Other / Unclassified** | `0.0` |
| 873 | songs | Adrianne Lenker | `` | **Other / Unclassified** | `0.0` |
| 874 | Music in A Foreign Language | Lloyd Cole | `` | **Other / Unclassified** | `0.0` |
| 875 | Citizen of Glass | Agnes Obel | `` | **Other / Unclassified** | `0.0` |
| 876 | Inner Song | Kelly Lee Owens | `` | **Other / Unclassified** | `0.0` |
| 877 | I Hear a New World | Joe Meek | `` | **Other / Unclassified** | `0.0` |
| 878 | 2 | Mac DeMarco | `indie, lo-fi indie` | **Pop** | `0.622` |
| 879 | Happy Soup | Baxter Dury | `` | **Other / Unclassified** | `0.0` |
| 880 | Open Here | Field Music | `` | **Other / Unclassified** | `0.0` |
| 881 | Anything in Return | Toro y Moi | `chillwave` | **Other / Unclassified** | `0.345` |
| 882 | 6 Feet Beneath the Moon | King Krule | `` | **Other / Unclassified** | `0.0` |
| 883 | The Delta Sweete | Bobbie Gentry | `` | **Other / Unclassified** | `0.0` |
| 884 | Night Thoughts | Suede | `britpop, madchester` | **Pop** | `0.362` |
| 885 | Norman Fucking Rockwell! | Lana Del Rey | `` | **Other / Unclassified** | `0.0` |
| 886 | Big Time | Angel Olsen | `` | **Other / Unclassified** | `0.0` |
| 887 | Ma | Devendra Banhart | `` | **Other / Unclassified** | `0.0` |
| 888 | Nothing's About to Happen to Me | Mitski | `` | **Other / Unclassified** | `0.0` |
| 889 | folklore | Taylor Swift | `` | **Other / Unclassified** | `0.0` |
| 890 | Mark Kozelek & Desertshore | Mark Kozelek | `slowcore` | **Other / Unclassified** | `0.29` |
| 891 | Oczy Mlody | The Flaming Lips | `neo-psychedelic` | **Rock** | `0.408` |
| 892 | Sinister Grift | Panda Bear | `neo-psychedelic` | **Rock** | `0.408` |
| 893 | Honeymoon | Lana Del Rey | `` | **Other / Unclassified** | `0.0` |
| 894 | Collapsed In Sunbeams | Arlo Parks | `` | **Other / Unclassified** | `0.0` |
| 895 | Punisher | Phoebe Bridgers | `` | **Other / Unclassified** | `0.0` |
| 896 | A Shaw Deal | Geologist | `` | **Other / Unclassified** | `0.0` |
| 897 | Debris | Keeley Forsyth | `` | **Other / Unclassified** | `0.0` |
| 898 | A New Place 2 Drown | Archy Marshall | `` | **Other / Unclassified** | `0.0` |
| 899 | Goodbye Emmanuelle (Bande originale du film) | Serge Gainsbourg | `chanson, variété française, french pop, french jazz, french house` | **Jazz** | `0.454` |
| 900 | Ciao Satan | Flavien Berger | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 901 | Talent Stick | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 902 | Baby Love | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 903 | Education & Recreation | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 904 | Recto Verso (Édition Augmentée) | Paradis | `french indie pop, french house, french pop` | **Pop** | `0.544` |
| 905 | Taormina | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 906 | Best Of Jacques Dutronc | Jacques Dutronc | `chanson, variété française, french pop, french house` | **Electronic** | `0.323` |
| 907 | Babel | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 908 | plouf! (Léviathan) | Flavien Berger | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 909 | Palais d'argile | Feu! Chatterton | `french indie pop, french pop, french house, chanson, variété française` | **Pop** | `0.544` |
| 910 | Innamorato | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 911 | Friendship Theme | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 912 | Colón Man | Equiknoxx | `dancehall, soca, dub techno` | **Reggae / Dub** | `0.614` |
| 913 | Travaux sur la n89 | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 914 | Mustango | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 915 | Breathe Deep | Oscar Jerome | `indie soul, jazz house, indie jazz, nu jazz` | **Jazz** | `0.701` |
| 916 | Two Windows | Lali Puna | `indie electronic, electropop, idm` | **Electronic** | `0.686` |
| 917 | Superb | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 918 | Secret Rhythms, Vol. 2 | Burnt Friedman | `krautrock, dub techno, idm, dub, avant-garde` | **Electronic** | `0.664` |
| 919 | Garden Party | Florent Marchet | `french pop, chanson, french house` | **Electronic** | `0.305` |
| 920 | Lightship 95 Sessions | Oscar Jerome | `indie soul, jazz house, indie jazz, nu jazz` | **Jazz** | `0.701` |
| 921 | Nymphs | Nicolas Jaar | `downtempo, electronica` | **Electronic** | `0.427` |
| 922 | Vivant | Malik Djoudi | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 923 | Late Night Tales: Air (Sampler) | Air | `trip hop, downtempo` | **Hip-Hop** | `0.369` |
| 924 | Léviathan | Flavien Berger | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 925 | Websites | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 926 | Vers les lueurs (Deluxe Edition) | Dominique A | `french pop, chanson, variété française, french indie pop, french house` | **Pop** | `0.504` |
| 927 | Secret Rhythms | Burnt Friedman | `krautrock, dub techno, idm, dub, avant-garde` | **Electronic** | `0.664` |
| 928 | Moscou | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 929 | Secret Rhythms, Vol. 4 | Burnt Friedman | `krautrock, dub techno, idm, dub, avant-garde` | **Electronic** | `0.664` |
| 930 | Cape Cira | K-Lone | `jazz house, uk garage, uk funky, dub techno` | **Electronic** | `0.587` |
| 931 | Confessions | Philippe Katerine | `french pop, chanson, variété française, french indie pop, french house` | **Pop** | `0.504` |
| 932 | Toute latitude | Dominique A | `french pop, chanson, variété française, french indie pop, french house` | **Pop** | `0.504` |
| 933 | Wisdom and Lies | Emperors New Clothes | `acid jazz, trip hop` | **Jazz** | `0.551` |
| 934 | Baby Love D.C. | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 935 | Natural Order 1982 - 1991 | Talk Talk | `new wave, synthpop` | **Electronic** | `0.493` |
| 936 | Collections 01 | Teebs | `idm` | **Electronic** | `0.371` |
| 937 | Labyrinthe | Feu! Chatterton | `french indie pop, french pop, french house, chanson, variété française` | **Pop** | `0.544` |
| 938 | Suburban Breeze | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 939 | Ouin Ouin | Miel De Montagne | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 940 | Petite Amie | Juliette Armanet | `french pop, variété française, chanson, french house, french indie pop` | **Pop** | `0.525` |
| 941 | La Musique / La Matière (Edition Spéciale) | Dominique A | `french pop, chanson, variété française, french indie pop, french house` | **Pop** | `0.504` |
| 942 | Spirales | Dominique A | `french pop, chanson, variété française, french indie pop, french house` | **Pop** | `0.504` |
| 943 | Frogs In A Pond | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 944 | Ouin Ouin Ouin | Miel De Montagne | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 945 | When We On | Crazy P | `nu disco, disco house, funky house` | **Electronic** | `0.492` |
| 946 | Iconoclasts | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 947 | Rave Age | Vitalic | `electroclash, french house, electro, electronica` | **Electronic** | `0.442` |
| 948 | Il Francese | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 949 | Tout Autour De Nous | Miel De Montagne | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 950 | knot of meanings | Nobukazu Takemura | `electroacoustic, glitch, shibuya-kei, idm, minimalism` | **Electronic** | `0.345` |
| 951 | N°2 | Serge Gainsbourg | `chanson, variété française, french pop, french jazz, french house` | **Jazz** | `0.454` |
| 952 | Tempéraments | Malik Djoudi | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 953 | Le Moujik Et Sa Femme | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 954 | The Complete Golden Ravedays | Superpitcher | `minimal techno` | **Ambient** | `0.51` |
| 955 | Study of the Invisible | Vanessa Wagner | `neoclassical, minimalism, electronic classical, contemporary classical` | **Classical** | `0.399` |
| 956 | Doubts and Convictions (Remastered) | Troublemakers | `trip hop` | **Hip-Hop** | `0.402` |
| 957 | Cheyenne Autumn | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 958 | contrebande 02. le disque de l'été | Flavien Berger | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 959 | Daylight Savings | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 960 | N°4 | Serge Gainsbourg | `chanson, variété française, french pop, french jazz, french house` | **Jazz** | `0.454` |
| 961 | Le manteau de pluie | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 962 | Idealist | Mind Enterprises | `italo disco, nu disco, disco house, italo dance` | **Electronic** | `0.485` |
| 963 | A place between us | Okvsho | `jazz house, nu jazz, indie jazz` | **Jazz** | `0.688` |
| 964 | Miel de Montagne | Miel De Montagne | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 965 | Dans cent ans | Flavien Berger | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 966 | All News Is Good News | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 967 | Tour de France 2022 (Live) | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 968 | Less Is Orchestra | Alias | `experimental hip hop, underground hip hop, trip hop` | **Hip-Hop** | `0.599` |
| 969 | No Human Tongue Can Tell | Radie Peat | `indie electronic` | **Electronic** | `0.62` |
| 970 | One More - Remixes | Yaeji | `` | **Other / Unclassified** | `0.0` |
| 971 | Aldorande | Aldorande | `jazz funk, nu jazz` | **Jazz** | `0.61` |
| 972 | New Decadence | Michelle Gurevich | `slowcore` | **Other / Unclassified** | `0.29` |
| 973 | Murat (Version Remasterisée 2019) | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 974 | Le monde réel | Dominique A | `french pop, chanson, variété française, french indie pop, french house` | **Pop** | `0.504` |
| 975 | Twentyears | Air | `trip hop, downtempo` | **Hip-Hop** | `0.369` |
| 976 | Late Night Tales presents Sasha: Scene Delete | Sasha | `trance, progressive house` | **Rock** | `0.407` |
| 977 | Couleurs Primaires | Paradis | `french indie pop, french house, french pop` | **Pop** | `0.544` |
| 978 | Hearts & Knives | Visage | `synthpop, new wave` | **Electronic** | `0.485` |
| 979 | A Secret Wish (2018 - Remaster) | Propaganda | `synthpop, new wave` | **Electronic** | `0.485` |
| 980 | Late Night Tales: Hot Chip | Hot Chip | `alternative dance, new rave, indie dance, indie electronic` | **Electronic** | `0.642` |
| 981 | Piedras 2 | Nicolas Jaar | `downtempo, electronica` | **Electronic** | `0.427` |
| 982 | Trip Tease | Tipsy | `exotica, plunderphonics, trip hop` | **Reggae / Dub** | `0.453` |
| 983 | Moon Safari Rarities (25th Anniversary Edition) | Air | `trip hop, downtempo` | **Hip-Hop** | `0.369` |
| 984 | Beauty Stab | ABC | `new wave, synthpop` | **Electronic** | `0.493` |
| 985 | When Will We Land? | Barry Can't Swim | `jazz house` | **Jazz** | `0.494` |
| 986 | The Spoon | Oscar Jerome | `indie soul, jazz house, indie jazz, nu jazz` | **Jazz** | `0.701` |
| 987 | Recto Verso | Paradis | `french indie pop, french house, french pop` | **Pop** | `0.544` |
| 988 | The Spork | Oscar Jerome | `indie soul, jazz house, indie jazz, nu jazz` | **Jazz** | `0.701` |
| 989 | A Rhythm Protects One | Call Super | `idm` | **Electronic** | `0.371` |
| 990 | Late Night Tales: Four Tet | Four Tet | `idm, electronica` | **Electronic** | `0.582` |
| 991 | YMO | YELLOW MAGIC ORCHESTRA | `synthpop, city pop, kayōkyoku, shibuya-kei` | **Pop** | `0.548` |
| 992 | The Fork | Oscar Jerome | `indie soul, jazz house, indie jazz, nu jazz` | **Jazz** | `0.701` |
| 993 | Michelangelo In Space ('Bunny'-Remix) | Charles Wilp | `` | **Other / Unclassified** | `0.0` |
| 994 | La vraie vie de Buck John | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 995 | Über Alles Director's Cut | Chilly Gonzales | `neoclassical` | **Other / Unclassified** | `0.247` |
| 996 | SBTRKT | SBTRKT | `` | **Other / Unclassified** | `0.0` |
| 997 | The Mountain Will Fall | DJ Shadow | `trip hop, plunderphonics, downtempo` | **Hip-Hop** | `0.506` |
| 998 | The Third Chimpanzee E.P. | Martin Gore | `synthpop` | **Pop** | `0.56` |
| 999 | The Triad | Pantha Du Prince | `minimal techno, idm` | **Electronic** | `0.572` |
| 1000 | Rare, Forever | Leon Vynehall | `lo-fi house, deep house` | **Electronic** | `0.216` |
| 1001 | The Consuming Flame: Open Exercises in Group Form | Matmos | `idm, plunderphonics, musique concrète, electroacoustic, experimental, glitch, avant-garde` | **Electronic** | `0.649` |
| 1002 | Ibifornia (Deluxe) | Cassius | `french house, disco house` | **Electronic** | `0.286` |
| 1003 | Mystère | La Femme | `french indie pop, french pop, french house` | **Pop** | `0.543` |
| 1004 | Los Angeles | Flying Lotus | `idm, experimental hip hop, nu jazz, glitch` | **Electronic** | `0.491` |
| 1005 | The Mix (2009 Remaster) | Kraftwerk | `krautrock, neue deutsche welle, synthpop, electronic, new wave, electro` | **Electronic** | `0.585` |
| 1006 | Spirit (Deluxe) | Depeche Mode | `new wave, synthpop, darkwave` | **Electronic** | `0.466` |
| 1007 | Ultimate Care II | Matmos | `idm, plunderphonics, musique concrète, electroacoustic, experimental, glitch, avant-garde` | **Electronic** | `0.649` |
| 1008 | Plastic Anniversary | Matmos | `idm, plunderphonics, musique concrète, electroacoustic, experimental, glitch, avant-garde` | **Electronic** | `0.649` |
| 1009 | DJ-Kicks | Kruder & Dorfmeister | `trip hop, downtempo, nu jazz, acid jazz` | **Jazz** | `0.658` |
| 1010 | The Art of the Lie | John Grant | `` | **Other / Unclassified** | `0.0` |
| 1011 | Happiness (Anniversary Edition) | Fridge | `post-rock, idm` | **Rock** | `0.511` |
| 1012 | For You And I | Loraine James | `idm, experimental` | **Electronic** | `0.334` |
| 1013 | Secret Life | Fred again.. | `stutter house, house, edm` | **Electronic** | `0.287` |
| 1014 | Tenement Symphony | Marc Almond | `synthpop, new wave` | **Electronic** | `0.485` |
| 1015 | Honey | Caribou | `idm` | **Electronic** | `0.371` |
| 1016 | Suddenly | Caribou | `idm` | **Electronic** | `0.371` |
| 1017 | Memento Mori | Depeche Mode | `new wave, synthpop, darkwave` | **Electronic** | `0.466` |
| 1018 | Season High | Little Dragon | `trip hop` | **Hip-Hop** | `0.402` |
| 1019 | Hyperdrama | Justice | `french house, new rave` | **Electronic** | `0.255` |
| 1020 | Laughing Stock | Talk Talk | `new wave, synthpop` | **Electronic** | `0.493` |
| 1021 | Strange Disciple | Nation of Language | `synthpop` | **Pop** | `0.56` |
| 1022 | Ardour | Teebs | `idm` | **Electronic** | `0.371` |
| 1023 | A Chance To Cut Is A Chance To Cure | Matmos | `idm, plunderphonics, musique concrète, electroacoustic, experimental, glitch, avant-garde` | **Electronic** | `0.649` |
| 1024 | Return to Archive | Matmos | `idm, plunderphonics, musique concrète, electroacoustic, experimental, glitch, avant-garde` | **Electronic** | `0.649` |
| 1025 | Human After All | Daft Punk | `french house, electronic, electro` | **Electronic** | `0.398` |
| 1026 | Late Night Tales: Barry Can't Swim (LNT Mix) | Barry Can't Swim | `jazz house` | **Jazz** | `0.494` |
| 1027 | Money Music | Surprise Chef | `indie jazz, jazz funk, jazz house` | **Jazz** | `0.711` |
| 1028 | In Daytona Yellow | Leon Vynehall | `lo-fi house, deep house` | **Electronic** | `0.216` |
| 1029 | Fossora | Björk | `art pop, trip hop` | **Hip-Hop** | `0.561` |
| 1030 | The Versions | Rhythm & Sound | `dub techno, dub, jazz house` | **Reggae / Dub** | `0.554` |
| 1031 | Late Night Tales: Music for Pleasure | Groove Armada | `big beat, trip hop` | **Hip-Hop** | `0.523` |
| 1032 | Consumed In Key | Richie Hawtin | `minimal techno, acid house, acid techno, idm, techno, dub techno` | **Electronic** | `0.749` |
| 1033 | Cenizas | Nicolas Jaar | `downtempo, electronica` | **Electronic** | `0.427` |
| 1034 | Bauhaus Staircase | Orchestral Manoeuvres In The Dark | `new wave, synthpop` | **Electronic** | `0.493` |
| 1035 | Late Night Tales: David Holmes | David Holmes | `trip hop, big beat` | **Hip-Hop** | `0.509` |
| 1036 | The Animal Spirits | James Holden | `gnawa, idm` | **Electronic** | `0.227` |
| 1037 | Architecture And Morality | Orchestral Manoeuvres In The Dark | `new wave, synthpop` | **Electronic** | `0.493` |
| 1038 | The Virgin Suicides Redux | Air | `trip hop, downtempo` | **Hip-Hop** | `0.369` |
| 1039 | Workaround | Beatrice Dillon | `electroacoustic, idm, experimental` | **Electronic** | `0.345` |
| 1040 | Sirens | Nicolas Jaar | `downtempo, electronica` | **Electronic** | `0.427` |
| 1041 | Random Access Memories | Daft Punk | `french house, electronic, electro` | **Electronic** | `0.398` |
| 1042 | Haha Sound | Broadcast | `dream pop, neo-psychedelic` | **Pop** | `0.503` |
| 1043 | Black Sands | Bonobo | `trip hop, downtempo, nu jazz, electronic` | **Jazz** | `0.601` |
| 1044 | MASSEDUCTION | St. Vincent | `art pop` | **Pop** | `0.549` |
| 1045 | LUMP | LUMP | `` | **Other / Unclassified** | `0.0` |
| 1046 | EP2 | Yaeji | `` | **Other / Unclassified** | `0.0` |
| 1047 | Just Landed | Burnt Friedman | `krautrock, dub techno, idm, dub, avant-garde` | **Electronic** | `0.664` |
| 1048 | 10th | Nobukazu Takemura | `electroacoustic, glitch, shibuya-kei, idm, minimalism` | **Electronic** | `0.345` |
| 1049 | Morituri | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 1050 | Committed Language | Laura Groves | `` | **Other / Unclassified** | `0.0` |
| 1051 | Dolores | Jean-Louis Murat | `french pop, chanson, variété française, french house` | **Electronic** | `0.349` |
| 1052 | Crèvecoeur (Super Deluxe Edition) | Daniel Darc | `french pop, chanson, french house, variété française` | **Pop** | `0.355` |
| 1053 | Dead Blue | Still Corners | `dream pop` | **Pop** | `0.472` |
| 1054 | Black Origami | Jlin | `footwork, idm, art pop, experimental` | **Electronic** | `0.529` |
| 1055 | Remember | Weval | `` | **Other / Unclassified** | `0.0` |
| 1056 | Fabiana Palladino | Fabiana Palladino | `` | **Other / Unclassified** | `0.0` |
| 1057 | Migration | Bonobo | `trip hop, downtempo, nu jazz, electronic` | **Jazz** | `0.601` |
| 1058 | Hideous Bastard | Oliver Sim | `indie electronic` | **Electronic** | `0.62` |
| 1059 | No Bad Memories | The Avalanches | `plunderphonics` | **Reggae / Dub** | `0.389` |
| 1060 | Holiday | The Magnetic Fields | `anti-folk` | **Folk / Country** | `0.383` |
| 1061 | Nabuma Rubberband | Little Dragon | `trip hop` | **Hip-Hop** | `0.402` |
| 1062 | Splendor & Misery | clipping. | `experimental hip hop, horrorcore, experimental, alternative hip hop` | **Hip-Hop** | `0.579` |
| 1063 | Love Letters | Metronomy | `` | **Other / Unclassified** | `0.0` |
| 1064 | Hissing Fauna, Are You The Destroyer? | of Montreal | `neo-psychedelic, baroque pop, art pop` | **Pop** | `0.684` |
| 1065 | ANIMA | Thom Yorke | `` | **Other / Unclassified** | `0.0` |
| 1066 | Metallic Life Review | Matmos | `idm, plunderphonics, musique concrète, electroacoustic, experimental, glitch, avant-garde` | **Electronic** | `0.649` |
| 1067 | Allbarone | Baxter Dury | `` | **Other / Unclassified** | `0.0` |
| 1068 | Everyday Robots | Damon Albarn | `` | **Other / Unclassified** | `0.0` |
| 1069 | Nocturne | Wild Nothing | `dream pop, shoegaze, chillwave` | **Rock** | `0.532` |
| 1070 | Give Up | The Postal Service | `` | **Other / Unclassified** | `0.0` |
| 1071 | Songs From The Big Chair | Tears For Fears | `new wave, synthpop` | **Electronic** | `0.493` |
| 1072 | Reflektor | Arcade Fire | `indie rock, baroque pop` | **Pop** | `0.691` |
| 1073 | Since I Left You | The Avalanches | `plunderphonics` | **Reggae / Dub** | `0.389` |
| 1074 | Congratulations | MGMT | `indie` | **Pop** | `0.591` |
| 1075 | Tremors | SOHN | `` | **Other / Unclassified** | `0.0` |
| 1076 | 69 Love Songs | The Magnetic Fields | `anti-folk` | **Folk / Country** | `0.383` |
| 1077 | Selections from 50 Song Memoir | The Magnetic Fields | `anti-folk` | **Folk / Country** | `0.383` |
| 1078 | I´m Coming Home | St. Thomas | `norsk rock, norwegian pop, anti-folk` | **Punk / Alternative** | `0.436` |
| 1079 | Rise Above It: A Souled American Anthology | Souled American | `alt country, slowcore, americana` | **Rock** | `0.461` |
| 1080 | Notes Campfire | Souled American | `alt country, slowcore, americana` | **Rock** | `0.461` |
| 1081 | Live At the Troubadour | Tim Buckley | `folk rock, folk` | **Folk / Country** | `0.671` |
| 1082 | YTI⅃AƎЯ | Bill Callahan | `alt country` | **Folk / Country** | `0.264` |
| 1083 | You Ain't Big / Alone Time / Peaceful Afternoon / Damsel In Distress / Trouble In Paradise | Rufus Wainwright | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1084 | Big Bad Luv | John Moreland | `americana, alt country, red dirt` | **Blues** | `0.413` |
| 1085 | Quickies | The Magnetic Fields | `anti-folk` | **Folk / Country** | `0.383` |
| 1086 | Gwendolyn | Jeff Tweedy | `alt country, americana, singer-songwriter` | **Folk / Country** | `0.507` |
| 1087 | Chicago 2017 | Daniel Johnston | `anti-folk` | **Folk / Country** | `0.383` |
| 1088 | Post To Wire | Richmond Fontaine | `alt country, americana` | **Folk / Country** | `0.396` |
| 1089 | With Light and with Love | Woods | `neo-psychedelic, space rock` | **Rock** | `0.562` |
| 1090 | Candlepower | Marina Allen | `` | **Other / Unclassified** | `0.0` |
| 1091 | Fun House | Hand Habits | `indie folk` | **Folk / Country** | `0.574` |
| 1092 | Rufus Wainwright (25th Anniversary Edition) | Rufus Wainwright | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1093 | Solid Air | John Martyn | `folk rock, folk` | **Folk / Country** | `0.671` |
| 1094 | Mala | Devendra Banhart | `` | **Other / Unclassified** | `0.0` |
| 1095 | One World | John Martyn | `folk rock, folk` | **Folk / Country** | `0.671` |
| 1096 | 5 Selections From 50 Song Memoir | The Magnetic Fields | `anti-folk` | **Folk / Country** | `0.383` |
| 1097 | A Country Dance | Joanna Sternberg | `anti-folk` | **Folk / Country** | `0.383` |
| 1098 | summerteeth (Deluxe Edition) | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1099 | Live On Boston Harbor | Fleet Foxes | `indie folk, folk, indie` | **Folk / Country** | `0.616` |
| 1100 | Sukierae | Tweedy | `alt country` | **Folk / Country** | `0.264` |
| 1101 | Rufus Wainwright and Amsterdam Sinfonietta (Live) | Rufus Wainwright | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1102 | Being There | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1103 | Blind Joe Death | John Fahey | `folk` | **Folk / Country** | `0.557` |
| 1104 | The Magical World of the Strands | Michael Head & The Strands | `folk rock` | **Folk / Country** | `0.611` |
| 1105 | Snocaps | Snocaps | `alt country` | **Folk / Country** | `0.264` |
| 1106 | Beware of the Maniacs | The Dodos | `` | **Other / Unclassified** | `0.0` |
| 1107 | Sunny, I Was Wrong | Joe Pernice | `power pop, jangle pop` | **Pop** | `0.319` |
| 1108 | Good Woman | Becca Mancari | `` | **Other / Unclassified** | `0.0` |
| 1109 | the stars are god's bullet holes. | John Murry | `americana, singer-songwriter` | **Folk / Country** | `0.539` |
| 1110 | Giant | Herman Düne | `anti-folk` | **Folk / Country** | `0.383` |
| 1111 | Ape in Pink Marble | Devendra Banhart | `` | **Other / Unclassified** | `0.0` |
| 1112 | Hey Mr Ferryman | Mark Eitzel | `slowcore, singer-songwriter, alt country` | **Pop** | `0.496` |
| 1113 | $10 Cowboy | Charley Crockett | `americana, outlaw country, alt country, red dirt, honky tonk, country` | **Folk / Country** | `0.479` |
| 1114 | Strange But True | Jad Fair | `anti-folk, noise rock` | **Folk / Country** | `0.507` |
| 1115 | Wanderer | Cat Power | `slowcore, singer-songwriter` | **R&B / Soul** | `0.416` |
| 1116 | Time Out Of Mind | Bob Dylan | `folk rock, folk, singer-songwriter, roots rock` | **Folk / Country** | `0.697` |
| 1117 | Sea Change | Beck | `anti-folk` | **Folk / Country** | `0.383` |
| 1118 | Bleeds | Wednesday | `alt country` | **Folk / Country** | `0.264` |
| 1119 | Hell-On | Neko Case | `alt country, southern gothic, americana` | **Folk / Country** | `0.422` |
| 1120 | To Enjoy is the Only Thing | Maple Glider | `indie folk` | **Folk / Country** | `0.574` |
| 1121 | Folkocracy | Rufus Wainwright | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1122 | My Echo | Laura Veirs | `indie folk` | **Folk / Country** | `0.574` |
| 1123 | New Morning | Bob Dylan | `folk rock, folk, singer-songwriter, roots rock` | **Folk / Country** | `0.697` |
| 1124 | Saint Cloud | Waxahatchee | `alt country` | **Folk / Country** | `0.264` |
| 1125 | Rain On Lens | Smog | `slowcore, anti-folk, alt country` | **Rock** | `0.472` |
| 1126 | I Get Into Trouble | Maple Glider | `indie folk` | **Folk / Country** | `0.574` |
| 1127 | Ode to Joy | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1128 | Unfollow The Rules | Rufus Wainwright | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1129 | Wilco (The Album) | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1130 | Rough and Rowdy Ways | Bob Dylan | `folk rock, folk, singer-songwriter, roots rock` | **Folk / Country** | `0.697` |
| 1131 | City Sun Eater in the River of Light | Woods | `neo-psychedelic, space rock` | **Rock** | `0.562` |
| 1132 | More Rain | M. Ward | `indie folk` | **Folk / Country** | `0.574` |
| 1133 | From A Basement On The Hill | Elliott Smith | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1134 | Apocalypse | Bill Callahan | `alt country` | **Folk / Country** | `0.264` |
| 1135 | The Lookout | Laura Veirs | `indie folk` | **Folk / Country** | `0.574` |
| 1136 | The Whole Love Expanded | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1137 | Sophie Auster | Sophie Auster | `` | **Other / Unclassified** | `0.0` |
| 1138 | Lorca | Tim Buckley | `folk rock, folk` | **Folk / Country** | `0.671` |
| 1139 | Twilight Override | Jeff Tweedy | `alt country, americana, singer-songwriter` | **Folk / Country** | `0.507` |
| 1140 | I Inside the Old Year Dying | PJ Harvey | `art pop, singer-songwriter, alternative rock` | **Pop** | `0.65` |
| 1141 | Together At Last | Jeff Tweedy | `alt country, americana, singer-songwriter` | **Folk / Country** | `0.507` |
| 1142 | A Ghost Is Born (Deluxe Version) | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1143 | Star Wars | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1144 | Schmilco | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1145 | Transistor Radio | M. Ward | `indie folk` | **Folk / Country** | `0.574` |
| 1146 | Cousin | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1147 | Shore | Fleet Foxes | `indie folk, folk, indie` | **Folk / Country** | `0.616` |
| 1148 | Everybody Knows This Is Nowhere | Neil Young | `classic rock, folk rock, singer-songwriter, roots rock` | **Rock** | `0.632` |
| 1149 | The New Eve Is Rising | The New Eves | `` | **Other / Unclassified** | `0.0` |
| 1150 | Manning Fireworks | MJ Lenderman | `alt country` | **Folk / Country** | `0.264` |
| 1151 | Woodland | Gillian Welch | `americana, bluegrass, alt country, folk, southern gothic, christian bluegrass` | **Folk / Country** | `0.723` |
| 1152 | Colour Green | Sibylle Baier | `folk` | **Folk / Country** | `0.557` |
| 1153 | Tigers Blood | Waxahatchee | `alt country` | **Folk / Country** | `0.264` |
| 1154 | You Want It Darker | Leonard Cohen | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1155 | The Whole Love (Deluxe Edition) | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1156 | Fox Confessor Brings The Flood (Bonus Track Version) | Neko Case | `alt country, southern gothic, americana` | **Folk / Country** | `0.422` |
| 1157 | Beast Epic | Iron & Wine | `indie folk` | **Folk / Country** | `0.574` |
| 1158 | Purple Mountains | Purple Mountains | `alt country` | **Folk / Country** | `0.264` |
| 1159 | What Will We Be | Devendra Banhart | `` | **Other / Unclassified** | `0.0` |
| 1160 | American IV: The Man Comes Around | Johnny Cash | `classic country, outlaw country, country` | **Folk / Country** | `0.276` |
| 1161 | Sky Blue Sky | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1162 | Shepherd in a Sheepskin Vest | Bill Callahan | `alt country` | **Folk / Country** | `0.264` |
| 1163 | I've Got Me | Joanna Sternberg | `anti-folk` | **Folk / Country** | `0.383` |
| 1164 | Bob Dylan's Greatest Hits Volume II | Bob Dylan | `folk rock, folk, singer-songwriter, roots rock` | **Folk / Country** | `0.697` |
| 1165 | Homegrown | Neil Young | `classic rock, folk rock, singer-songwriter, roots rock` | **Rock** | `0.632` |
| 1166 | American Water | Silver Jews | `alt country, anti-folk` | **Folk / Country** | `0.374` |
| 1167 | Gold Record | Bill Callahan | `alt country` | **Folk / Country** | `0.264` |
| 1168 | The Navigator | Hurray For The Riff Raff | `americana, alt country` | **Folk / Country** | `0.404` |
| 1169 | Crack-Up | Fleet Foxes | `indie folk, folk, indie` | **Folk / Country** | `0.616` |
| 1170 | Infidels | Bob Dylan | `folk rock, folk, singer-songwriter, roots rock` | **Folk / Country** | `0.697` |
| 1171 | Cruel Country | Wilco | `alt country, americana, indie rock` | **Rock** | `0.627` |
| 1172 | Song For Our Daughter | Laura Marling | `singer-songwriter, southern gothic, folk, indie folk` | **Folk / Country** | `0.651` |
| 1173 | False Lankum | Lankum | `folk, traditional folk, southern gothic, neofolk, celtic` | **Folk / Country** | `0.547` |
| 1174 | Ignorance | The Weather Station | `indie folk` | **Folk / Country** | `0.574` |
| 1175 | A Crow Looked at Me | Mount Eerie | `slowcore, anti-folk, indie folk` | **Rock** | `0.607` |
| 1176 | Rat Saw God | Wednesday | `alt country` | **Folk / Country** | `0.264` |
| 1177 | Years to Burn | Calexico | `alt country, americana, roots rock` | **Rock** | `0.546` |
| 1178 | Pink Moon | Nick Drake | `folk, singer-songwriter` | **Folk / Country** | `0.677` |
| 1179 | Ladies of the Canyon | Joni Mitchell | `folk, folk rock, singer-songwriter` | **Folk / Country** | `0.711` |
| 1180 | Birds of Paradise | Thomas Dollbaum | `alt country` | **Folk / Country** | `0.264` |
| 1181 | Colors | Beck | `anti-folk` | **Folk / Country** | `0.383` |
| 1182 | a Mouse in a Crowded House | St. Thomas | `norsk rock, norwegian pop, anti-folk` | **Punk / Alternative** | `0.436` |
| 1183 | The Glow, Pt. 2 | The Microphones | `slowcore, anti-folk, lo-fi indie, indie folk` | **Rock** | `0.658` |
| 1184 | Little Wide Open | Kevin Morby | `` | **Other / Unclassified** | `0.0` |
| 1185 | Please Be Mine | Molly Burch | `` | **Other / Unclassified** | `0.0` |
| 1186 | Colorado | Neil Young | `classic rock, folk rock, singer-songwriter, roots rock` | **Rock** | `0.632` |
| 1187 | Buck Meek | Buck Meek | `` | **Other / Unclassified** | `0.0` |
| 1188 | Time Fades Away | Neil Young | `classic rock, folk rock, singer-songwriter, roots rock` | **Rock** | `0.632` |
| 1189 | Jassbusters | Connan Mockasin | `` | **Other / Unclassified** | `0.0` |
| 1190 | Frozen | Souled American | `alt country, slowcore, americana` | **Rock** | `0.461` |
| 1191 | Lucinda Williams (Deluxe Edition) | Lucinda Williams | `alt country, americana, outlaw country, singer-songwriter, folk` | **Folk / Country** | `0.681` |
| 1192 | The Canyon | JJerome87 | `` | **Other / Unclassified** | `0.0` |
| 1193 | Tropical Dandy | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 1194 | Elliott Smith | Elliott Smith | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1195 | I Love You, Honeybear | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 1196 | Ask Me Tomorrow | Mojave 3 | `slowcore, dream pop, shoegaze` | **Rock** | `0.494` |
| 1197 | WARM | Jeff Tweedy | `alt country, americana, singer-songwriter` | **Folk / Country** | `0.507` |
| 1198 | Love Is The King | Jeff Tweedy | `` | **Other / Unclassified** | `0.0` |
| 1199 | I Know I'm Funny haha | Faye Webster | `` | **Other / Unclassified** | `0.0` |
| 1200 | Release The Stars | Rufus Wainwright | `singer-songwriter` | **R&B / Soul** | `0.441` |
| 1201 | Bobbie Gentry's The Delta Sweete Revisited | Mercury Rev | `neo-psychedelic, shoegaze` | **Rock** | `0.473` |
| 1202 | Fear Fun | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 1203 | Haunted Mountain | Buck Meek | `` | **Other / Unclassified** | `0.0` |
| 1204 | The Purple Bird | Bonnie Prince Billy | `alt country, americana` | **Folk / Country** | `0.396` |
| 1205 | U.F.O.F. | Big Thief | `` | **Other / Unclassified** | `0.0` |
| 1206 | Rain Dogs | Tom Waits | `singer-songwriter, southern gothic` | **R&B / Soul** | `0.42` |
| 1207 | The Hope Six Demolition Project | PJ Harvey | `art pop, singer-songwriter, alternative rock` | **Pop** | `0.65` |
| 1208 | My Days of 58 | Bill Callahan | `alt country` | **Folk / Country** | `0.264` |
| 1209 | Ride Lonesome | Beck | `anti-folk` | **Folk / Country** | `0.383` |
| 1210 | The Glad Fact | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1211 | Lotta Sea Lice | Courtney Barnett | `` | **Other / Unclassified** | `0.0` |
| 1212 | Double Infinity | Big Thief | `` | **Other / Unclassified** | `0.0` |
| 1213 | Sling | Clairo | `bedroom pop` | **Pop** | `0.378` |
| 1214 | Memories Are Now | Jesca Hoop | `indie folk` | **Folk / Country** | `0.574` |
| 1215 | Foxwarren | Foxwarren | `` | **Other / Unclassified** | `0.0` |
| 1216 | Blue Morpho | Ed O'Brien | `` | **Other / Unclassified** | `0.0` |
| 1217 | King Cobra | Infinity Knives | `experimental hip hop` | **Hip-Hop** | `0.512` |
| 1218 | DAMN. | Kendrick Lamar | `hip hop, west coast hip hop` | **Hip-Hop** | `0.632` |
| 1219 | Of Light | Shabazz Palaces | `experimental hip hop, alternative hip hop` | **Hip-Hop** | `0.536` |
| 1220 | Shabazz Palaces | Shabazz Palaces | `experimental hip hop, alternative hip hop` | **Hip-Hop** | `0.536` |
| 1221 | Bring Backs | Alfa Mist | `nu jazz, jazz rap, indie jazz, jazz fusion, jazz` | **Jazz** | `0.757` |
| 1222 | Visions of Bodies Being Burned | clipping. | `experimental hip hop, horrorcore, experimental, alternative hip hop` | **Hip-Hop** | `0.579` |
| 1223 | SOUR SOUL | BADBADNOTGOOD | `` | **Other / Unclassified** | `0.0` |
| 1224 | Black Up | Shabazz Palaces | `experimental hip hop, alternative hip hop` | **Hip-Hop** | `0.536` |
| 1225 | Where I'm Meant To Be | Ezra Collective | `jazz rap, indie soul, nu jazz` | **Jazz** | `0.687` |
| 1226 | We got it from Here... Thank You 4 Your service | A Tribe Called Quest | `jazz rap, east coast hip hop, old school hip hop, hip hop` | **Hip-Hop** | `0.659` |
| 1227 | The Don Of Diamond Dreams | Shabazz Palaces | `experimental hip hop, alternative hip hop` | **Hip-Hop** | `0.536` |
| 1228 | Lese Majesty | Shabazz Palaces | `experimental hip hop, alternative hip hop` | **Hip-Hop** | `0.536` |
| 1229 | Cancer 4 Cure | El-P | `experimental hip hop` | **Hip-Hop** | `0.512` |
| 1230 | The In Sound From Way Out! | Beastie Boys | `rap rock, old school hip hop, east coast hip hop, hip hop` | **Hip-Hop** | `0.69` |
| 1231 | LOGGERHEAD | Wu-Lu | `experimental hip hop` | **Hip-Hop** | `0.512` |
| 1232 | DeBÍ TiRAR MáS FOToS | Bad Bunny | `reggaeton, trap latino, latin, urbano latino` | **Latin / World** | `0.695` |
| 1233 | Paul's Boutique (20th Anniversary Edition / Remastered) | Beastie Boys | `rap rock, old school hip hop, east coast hip hop, hip hop` | **Hip-Hop** | `0.69` |
| 1234 | Quazarz: Born on a Gangster Star | Shabazz Palaces | `experimental hip hop, alternative hip hop` | **Hip-Hop** | `0.536` |
| 1235 | cLOUDDEAD (2024 Remastered) | cLOUDDEAD | `experimental hip hop, cloud rap` | **Hip-Hop** | `0.533` |
| 1236 | The Grind Date (20th Anniversary Edition) | De La Soul | `jazz rap, east coast hip hop` | **Jazz** | `0.615` |
| 1237 | The Divine Feminine | Mac Miller | `` | **Other / Unclassified** | `0.0` |
| 1238 | RTJ4 | Run The Jewels | `hip hop` | **Hip-Hop** | `0.59` |
| 1239 | Heavy Heavy | Young Fathers | `experimental hip hop` | **Hip-Hop** | `0.512` |
| 1240 | Athletic Progression | Athletic Progression | `nu jazz, jazz rap, indie jazz, experimental jazz` | **Jazz** | `0.746` |
| 1241 | Natural Brown Prom Queen | Sudan Archives | `alternative r&b, indie soul` | **R&B / Soul** | `0.626` |
| 1242 | To Pimp A Butterfly | Kendrick Lamar | `hip hop, west coast hip hop` | **Hip-Hop** | `0.632` |
| 1243 | Cheat Codes | Danger Mouse | `` | **Other / Unclassified** | `0.0` |
| 1244 | To Know Without Knowing | Mulatu Astatke | `ethiopian jazz, jazz` | **Jazz** | `0.65` |
| 1245 | Light Years Away | Ronald Langestraat | `soul jazz` | **Jazz** | `0.611` |
| 1246 | Trumpets of Michel-Ange | Ibrahim Maalouf | `french jazz, jazz` | **Jazz** | `0.675` |
| 1247 | Goodbye, Porkpie Hat | Charles Mingus | `jazz, hard bop, bebop, free jazz, cool jazz, jazz ballads` | **Jazz** | `0.753` |
| 1248 | Special recueil-souvenir à la mémoire d'Aboubacar Demba Camara (Bolibana Collection) | Bembeya Jazz National | `ethiopian jazz, highlife, afrobeat` | **Jazz** | `0.645` |
| 1249 | Displaced Diaspora | Moses Boyd | `nu jazz, indie jazz, jazz` | **Jazz** | `0.727` |
| 1250 | A Night At Club Baobab (Senegalese Dance Music of the 70's) | Orchestra Baobab | `afro-cuban jazz, afropop` | **Latin / World** | `0.603` |
| 1251 | Authenticité 73 - Parade Africaine | Bembeya Jazz National | `ethiopian jazz, highlife, afrobeat` | **Jazz** | `0.645` |
| 1252 | Wede Harer Guzo | Hailu Mergia | `ethiopian jazz` | **Jazz** | `0.556` |
| 1253 | Apollo | Ronald Langestraat | `soul jazz` | **Jazz** | `0.611` |
| 1254 | Jerusalem | Emahoy Tsege Mariam Gebru | `ethiopian jazz` | **Jazz** | `0.556` |
| 1255 | Being Human Being | Erik Truffaz | `nu jazz, french jazz, jazz, jazz fusion` | **Jazz** | `0.735` |
| 1256 | Introducing Christian Scott | Christian Scott aTunde Adjuah | `jazz, nu jazz, experimental jazz, indie jazz, jazz fusion` | **Jazz** | `0.776` |
| 1257 | FATHERS | Nate Smith | `jazz fusion, soul jazz, indie jazz, nu jazz, jazz funk, jazz` | **Jazz** | `0.772` |
| 1258 | India | Gal Costa | `mpb, bossa nova, brazilian jazz` | **Latin / World** | `0.615` |
| 1259 | Soul Jazz Records presents MIAMI SOUND: Rare Funk & Soul From Miami, Florida 1967-74 | Soul Jazz Records Presents | `soul jazz` | **Jazz** | `0.611` |
| 1260 | Yellow | Emma-Jean Thackray | `nu jazz, acid jazz, indie jazz` | **Jazz** | `0.718` |
| 1261 | Sunshine Remixed | Hector Plimmer | `indie jazz, soul jazz` | **Jazz** | `0.705` |
| 1262 | 00-237 XP-I | Magic Malik Orchestra | `french jazz, experimental jazz, nu jazz, jazz fusion, afro-cuban jazz, indie jazz` | **Jazz** | `0.763` |
| 1263 | Volume 1 | Miles Davis | `jazz, cool jazz, hard bop, bebop, jazz fusion, jazz ballads, free jazz` | **Jazz** | `0.789` |
| 1264 | Blume | Nérija | `nu jazz, jazz, indie jazz` | **Jazz** | `0.725` |
| 1265 | Discothèque 76 | Bembeya Jazz National | `ethiopian jazz, highlife, afrobeat` | **Jazz** | `0.645` |
| 1266 | Yusef Lateef's Detroit Latitude 42º 30º Longitude 83º | Yusef Lateef | `jazz, hard bop, free jazz, avant-garde, cool jazz` | **Jazz** | `0.777` |
| 1267 | Doni Doni | Erik Truffaz | `nu jazz, french jazz, jazz, jazz fusion` | **Jazz** | `0.735` |
| 1268 | Fancy Dancer (Reissue) | Bobbi Humphrey | `jazz funk, jazz fusion, soul jazz` | **Jazz** | `0.716` |
| 1269 | NOT TiGHT | DOMi & JD BECK | `jazz fusion, nu jazz` | **Jazz** | `0.663` |
| 1270 | Songs Of Resistance 1942 - 2018 | Marc Ribot | `afro-cuban jazz, free jazz` | **Jazz** | `0.666` |
| 1271 | Here And There | Kibrom Birhane | `ethiopian jazz` | **Jazz** | `0.556` |
| 1272 | Quarteto Jobim-Morelenbaum | Quarteto Jobim-Morelenbaum | `` | **Other / Unclassified** | `0.0` |
| 1273 | Promeneur | Mathieu Boogaerts | `french jazz, french pop, chanson` | **Jazz** | `0.545` |
| 1274 | Baïne | mohs. | `nu jazz, indie jazz` | **Jazz** | `0.683` |
| 1275 | Sunshine | Hector Plimmer | `indie jazz, soul jazz` | **Jazz** | `0.705` |
| 1276 | 華麗なるエレクトーン -ザ・ワード- | SHIGEO SEKITO | `jazz fusion` | **Jazz** | `0.644` |
| 1277 | Friends & Family | DARGZ | `` | **Other / Unclassified** | `0.0` |
| 1278 | Palo Alto | Thelonious Monk | `jazz, bebop, hard bop, cool jazz, free jazz` | **Jazz** | `0.799` |
| 1279 | Someday My Prince Will Come | Miles Davis | `jazz, cool jazz, hard bop, bebop, jazz fusion, jazz ballads, free jazz` | **Jazz** | `0.789` |
| 1280 | Basra (Remastered) | Pete La Roca | `hard bop, free jazz, jazz, bebop` | **Jazz** | `0.753` |
| 1281 | Brand New Life | Brandee Younger | `experimental jazz, jazz` | **Jazz** | `0.68` |
| 1282 | Empyrean Isles (Expanded Edition) | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1283 | The Kicker | Bobby Hutcherson | `hard bop, jazz, free jazz, jazz funk, jazz ballads, bebop, cool jazz` | **Jazz** | `0.746` |
| 1284 | Blossom Dearie (Expanded Edition) | Blossom Dearie | `french jazz, vocal jazz, jazz` | **Jazz** | `0.725` |
| 1285 | Introducing Johnny Griffin (Rudy Van Gelder Edition / Remastered) | Johnny Griffin | `hard bop, jazz ballads, jazz, bebop` | **Jazz** | `0.64` |
| 1286 | Happenings | Bobby Hutcherson | `hard bop, jazz, free jazz, jazz funk, jazz ballads, bebop, cool jazz` | **Jazz** | `0.746` |
| 1287 | Drums Around The Corner | Art Blakey | `hard bop, bebop, jazz, afro-cuban jazz` | **Jazz** | `0.679` |
| 1288 | My Point Of View (Expanded Edition) | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1289 | Spectrum | Billy Cobham | `jazz fusion, jazz funk, jazz` | **Jazz** | `0.756` |
| 1290 | Horace Silver Trio | Horace Silver | `hard bop, jazz, bebop, cool jazz, soul jazz, jazz ballads` | **Jazz** | `0.693` |
| 1291 | Secrets | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1292 | Sketches of Spain | Gil Evans | `jazz, cool jazz, big band, hard bop, bebop, free jazz` | **Jazz** | `0.78` |
| 1293 | Suite 16 | Yusef Lateef | `jazz, hard bop, free jazz, avant-garde, cool jazz` | **Jazz** | `0.777` |
| 1294 | Tetragon | Joe Henderson | `hard bop, jazz, jazz ballads, bebop, cool jazz, free jazz` | **Jazz** | `0.754` |
| 1295 | Scenes From Above | Julian Lage | `jazz` | **Jazz** | `0.633` |
| 1296 | Mary Lou Williams | Mary Lou Williams | `jazz, bebop, swing music` | **Jazz** | `0.798` |
| 1297 | Horace-Scope | Horace Silver Quintet | `hard bop, bebop, jazz, jazz ballads, cool jazz, soul jazz` | **Jazz** | `0.697` |
| 1298 | Pax | Andrew Hill | `free jazz, hard bop, jazz, experimental jazz, avant-garde, bebop` | **Jazz** | `0.823` |
| 1299 | Groove Yard | The Montgomery Brothers | `hard bop, cool jazz, jazz, bebop` | **Jazz** | `0.688` |
| 1300 | Mosaic (The Rudy Van Gelder Edition) | Art Blakey & The Jazz Messengers | `hard bop, jazz, bebop, cool jazz` | **Jazz** | `0.685` |
| 1301 | Mulatu Plays Mulatu | Mulatu Astatke | `ethiopian jazz, jazz` | **Jazz** | `0.65` |
| 1302 | Arthur Verocai | Arthur Verocai | `brazilian jazz, bossa nova, mpb` | **Latin / World** | `0.605` |
| 1303 | Blues Walk | Lou Donaldson | `hard bop, jazz, soul jazz, bebop, jazz ballads, jazz funk, cool jazz` | **Jazz** | `0.707` |
| 1304 | The Great Pretender | Lester Bowie | `free jazz, avant-garde, experimental jazz, jazz` | **Jazz** | `0.797` |
| 1305 | Inventions And Dimensions (Expanded Edition) | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1306 | Y Los Cubanos Postizos | Marc Ribot | `` | **Other / Unclassified** | `0.0` |
| 1307 | THE CHAMP | Jimmy Smith | `hard bop, soul jazz, jazz, jazz funk, cool jazz` | **Jazz** | `0.692` |
| 1308 | Mr. Hands | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1309 | Speak Like A Child (Expanded Edition) | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1310 | It's Time | Jackie McLean | `hard bop, bebop, jazz, free jazz, jazz ballads` | **Jazz** | `0.708` |
| 1311 | In the Moment (Deluxe Edition) | Makaya McCraven | `nu jazz, experimental jazz, indie jazz, jazz, free jazz` | **Jazz** | `0.787` |
| 1312 | The Turnaround | Hank Mobley | `hard bop, jazz, bebop, cool jazz, jazz ballads` | **Jazz** | `0.667` |
| 1313 | Silver's Blue | Horace Silver | `hard bop, jazz, bebop, cool jazz, soul jazz, jazz ballads` | **Jazz** | `0.693` |
| 1314 | Everybody Digs Bill Evans | Bill Evans | `jazz, cool jazz, jazz ballads, hard bop, bebop` | **Jazz** | `0.697` |
| 1315 | The Cooker | Lee Morgan | `hard bop, jazz, bebop, jazz ballads, cool jazz` | **Jazz** | `0.691` |
| 1316 | Mwandishi | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1317 | New York Is Now! | Ornette Coleman | `free jazz, jazz, avant-garde, experimental jazz, hard bop, bebop` | **Jazz** | `0.827` |
| 1318 | Naked City | John Zorn | `free jazz, avant-garde, experimental jazz, experimental, musique concrète` | **Jazz** | `0.757` |
| 1319 | Quiet Kenny | Kenny Dorham | `hard bop, jazz, afro-cuban jazz, bebop, jazz ballads, cool jazz, latin jazz` | **Jazz** | `0.696` |
| 1320 | The Quest | Mal Waldron | `hard bop, jazz, free jazz, cool jazz, bebop` | **Jazz** | `0.764` |
| 1321 | Songs For Sinners | Moses Boyd | `` | **Other / Unclassified** | `0.0` |
| 1322 | Today And Tomorrow | McCoy Tyner | `jazz, hard bop, jazz ballads, cool jazz, bebop, free jazz` | **Jazz** | `0.775` |
| 1323 | Born to Be Blue | Chet Baker | `jazz, cool jazz, vocal jazz, jazz ballads` | **Jazz** | `0.697` |
| 1324 | Page One | Joe Henderson | `hard bop, jazz, jazz ballads, bebop, cool jazz, free jazz` | **Jazz** | `0.754` |
| 1325 | The Complete Town Hall Concert (Live) | Charles Mingus | `jazz, hard bop, bebop, free jazz, cool jazz, jazz ballads` | **Jazz** | `0.753` |
| 1326 | Coleman Hawkins Encounters Ben Webster (Expanded Edition) | Coleman Hawkins | `jazz, jazz ballads, bebop, cool jazz, hard bop, swing music` | **Jazz** | `0.712` |
| 1327 | The Best Of Lee Morgan | Lee Morgan | `hard bop, jazz, bebop, jazz ballads, cool jazz` | **Jazz** | `0.691` |
| 1328 | Ben Webster Meets Oscar Peterson | Oscar Peterson | `jazz, jazz ballads, cool jazz, bebop, vocal jazz, hard bop` | **Jazz** | `0.707` |
| 1329 | Horace - Scope | Horace Silver | `hard bop, jazz, bebop, cool jazz, soul jazz, jazz ballads` | **Jazz** | `0.693` |
| 1330 | Mata | Akalé Wubé | `ethiopian jazz, afrobeat` | **Jazz** | `0.597` |
| 1331 | Akalé Wubé | Akalé Wubé | `ethiopian jazz, afrobeat` | **Jazz** | `0.597` |
| 1332 | Pirates Choice | Orchestra Baobab | `afro-cuban jazz, afropop` | **Latin / World** | `0.603` |
| 1333 | The Blues and the Abstract Truth | Oliver Nelson | `hard bop, jazz, bebop, cool jazz, big band` | **Jazz** | `0.659` |
| 1334 | Les Liaisons Dangereuses 1960 | Art Blakey | `hard bop, bebop, jazz, afro-cuban jazz` | **Jazz** | `0.679` |
| 1335 | Salt River | Sam Amidon | `indie folk` | **Folk / Country** | `0.574` |
| 1336 | Music For Lovers | Lee Morgan | `hard bop, jazz, bebop, jazz ballads, cool jazz` | **Jazz** | `0.691` |
| 1337 | Symbiosis | Bill Evans | `jazz, cool jazz, jazz ballads, hard bop, bebop` | **Jazz** | `0.697` |
| 1338 | Dark Matter | Moses Boyd | `nu jazz, indie jazz, jazz` | **Jazz** | `0.727` |
| 1339 | Black Classical Music | Yussef Dayes | `nu jazz, indie jazz, jazz fusion` | **Jazz** | `0.741` |
| 1340 | Big Band Bossa Nova | Quincy Jones | `soul jazz, big band, quiet storm` | **R&B / Soul** | `0.585` |
| 1341 | Bags & Trane | Milt Jackson & John Coltrane | `hard bop, bebop` | **Jazz** | `0.3` |
| 1342 | Hyper-Dimensional Expansion Beam | The Comet Is Coming | `nu jazz, experimental jazz, indie jazz, jazz fusion` | **Jazz** | `0.757` |
| 1343 | Getz/Gilberto #2 | Stan Getz | `bossa nova, jazz, brazilian jazz, cool jazz, latin jazz, jazz ballads` | **Latin / World** | `0.69` |
| 1344 | The Amazing Bud Powell, Vol. 3: Bud! | Bud Powell | `bebop, jazz, hard bop, cool jazz` | **Jazz** | `0.716` |
| 1345 | Could We Be More | Kokoroko | `` | **Other / Unclassified** | `0.0` |
| 1346 | The Original Misty | Erroll Garner | `jazz, jazz ballads, hard bop, cool jazz` | **Jazz** | `0.655` |
| 1347 | Gal Costa | Gal Costa | `mpb, bossa nova, brazilian jazz` | **Latin / World** | `0.615` |
| 1348 | Lanquidity (Definitive Edition) | Sun Ra | `free jazz, experimental jazz, jazz, avant-garde, hard bop` | **Jazz** | `0.79` |
| 1349 | Clube Da Esquina | Milton Nascimento | `mpb, bossa nova, brazilian jazz` | **Latin / World** | `0.615` |
| 1350 | Lester Young With The Oscar Peterson Trio | Lester Young | `jazz, cool jazz, bebop, jazz ballads` | **Jazz** | `0.715` |
| 1351 | Money Jungle (Expanded Edition / 2002 Remaster) | Duke Ellington | `jazz, big band, swing music, cool jazz, jazz ballads` | **Jazz** | `0.68` |
| 1352 | Out Of The Cool | The Gil Evans Orchestra | `cool jazz, big band, jazz, hard bop, bebop` | **Jazz** | `0.666` |
| 1353 | Heaven and Earth | Kamasi Washington | `jazz` | **Jazz** | `0.633` |
| 1354 | Seven Steps To Heaven (Expanded Edition) | Miles Davis | `jazz, cool jazz, hard bop, bebop, jazz fusion, jazz ballads, free jazz` | **Jazz** | `0.789` |
| 1355 | Black To The Future | Sons Of Kemet | `experimental jazz, nu jazz, jazz, indie jazz, acid jazz` | **Jazz** | `0.763` |
| 1356 | Tribute to Ndiouga Dieng | Orchestra Baobab | `afro-cuban jazz, afropop` | **Latin / World** | `0.603` |
| 1357 | Lala Belu | Hailu Mergia | `ethiopian jazz` | **Jazz** | `0.556` |
| 1358 | Both Directions At Once: The Lost Album (Deluxe Version) | John Coltrane | `jazz, hard bop, free jazz, bebop, jazz ballads, cool jazz` | **Jazz** | `0.761` |
| 1359 | We're New Here | Gil Scott-Heron | `spoken word, jazz funk` | **R&B / Soul** | `0.518` |
| 1360 | Universal Beings (IA11 Edition) | Makaya McCraven | `nu jazz, experimental jazz, indie jazz, jazz, free jazz` | **Jazz** | `0.787` |
| 1361 | Gula Matari | Quincy Jones | `soul jazz, big band, quiet storm` | **R&B / Soul** | `0.585` |
| 1362 | Eastern Sounds (Remastered 2023) | Yusef Lateef | `jazz, hard bop, free jazz, avant-garde, cool jazz` | **Jazz** | `0.777` |
| 1363 | Souvenirs | Emahoy Tsege Mariam Gebru | `ethiopian jazz` | **Jazz** | `0.556` |
| 1364 | WHO ASKED? | DOMi & JD BECK | `jazz fusion, nu jazz` | **Jazz** | `0.663` |
| 1365 | The Stardust Road | Hoagy Carmichael | `big band, ragtime` | **Metal** | `0.384` |
| 1366 | The Dude | Quincy Jones | `soul jazz, big band, quiet storm` | **R&B / Soul** | `0.585` |
| 1367 | Fearless Movement | Kamasi Washington | `jazz` | **Jazz** | `0.633` |
| 1368 | Your Queen Is A Reptile | Sons Of Kemet | `experimental jazz, nu jazz, jazz, indie jazz, acid jazz` | **Jazz** | `0.763` |
| 1369 | Black Focus | Yussef Kamaal | `nu jazz, jazz fusion, indie jazz, experimental jazz, jazz funk, jazz` | **Jazz** | `0.766` |
| 1370 | Duke Ellington & John Coltrane | Duke Ellington | `jazz, big band, swing music, cool jazz, jazz ballads` | **Jazz** | `0.68` |
| 1371 | Portrait | Ben Webster | `jazz, jazz ballads, cool jazz, bebop` | **Jazz** | `0.699` |
| 1372 | The Epic | Kamasi Washington | `jazz` | **Jazz** | `0.633` |
| 1373 | Pieces of a Man | Gil Scott-Heron | `spoken word, jazz funk` | **R&B / Soul** | `0.518` |
| 1374 | Maiden Voyage (Remastered 1999/Rudy Van Gelder Edition) | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1375 | The Hawk Relaxes | Coleman Hawkins | `jazz, jazz ballads, bebop, cool jazz, hard bop, swing music` | **Jazz** | `0.712` |
| 1376 | Bending New Corners | Erik Truffaz | `nu jazz, french jazz, jazz, jazz fusion` | **Jazz** | `0.735` |
| 1377 | Franks Wild Years | Tom Waits | `singer-songwriter, southern gothic` | **R&B / Soul** | `0.42` |
| 1378 | Vertigo | Jackie McLean | `hard bop, bebop, jazz, free jazz, jazz ballads` | **Jazz** | `0.708` |
| 1379 | The Ground | Tord Gustavsen Trio | `jazz, ambient jazz` | **Jazz** | `0.713` |
| 1380 | Miles Smiles | Miles Davis | `jazz, cool jazz, hard bop, bebop, jazz fusion, jazz ballads, free jazz` | **Jazz** | `0.789` |
| 1381 | I Put A Spell On You | Nina Simone | `vocal jazz, soul jazz, soul, jazz` | **Jazz** | `0.75` |
| 1382 | Kofi | Donald Byrd | `hard bop, jazz funk, jazz, soul jazz, jazz fusion, acid jazz, bebop` | **Jazz** | `0.751` |
| 1383 | The Cape Verdean Blues | Horace Silver Quintet | `hard bop, bebop, jazz, jazz ballads, cool jazz, soul jazz` | **Jazz** | `0.697` |
| 1384 | Mr. Shing-A-Ling | Lou Donaldson | `hard bop, jazz, soul jazz, bebop, jazz ballads, jazz funk, cool jazz` | **Jazz** | `0.707` |
| 1385 | The Gigolo | Lee Morgan | `hard bop, jazz, bebop, jazz ballads, cool jazz` | **Jazz** | `0.691` |
| 1386 | Alfie | Sonny Rollins | `hard bop, jazz, bebop, jazz ballads, cool jazz, free jazz` | **Jazz** | `0.762` |
| 1387 | Crystal Spears | Sun Ra | `free jazz, experimental jazz, jazz, avant-garde, hard bop` | **Jazz** | `0.79` |
| 1388 | The End Of An Ear | Robert Wyatt | `art rock, progressive rock, experimental, krautrock` | **Rock** | `0.673` |
| 1389 | Mingus Plays Piano | Charles Mingus | `jazz, hard bop, bebop, free jazz, cool jazz, jazz ballads` | **Jazz** | `0.753` |
| 1390 | Head Hunters | Herbie Hancock | `jazz, jazz fusion, jazz funk, hard bop, cool jazz` | **Jazz** | `0.735` |
| 1391 | Sinatra At The Sands | Frank Sinatra | `christmas, big band, adult standards, swing music, jazz, vocal jazz` | **Jazz** | `0.643` |
| 1392 | Silent Movies | Marc Ribot | `` | **Other / Unclassified** | `0.0` |
| 1393 | Blackstar | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1394 | Like Someone In Love | Art Blakey & The Jazz Messengers | `hard bop, jazz, bebop, cool jazz` | **Jazz** | `0.685` |
| 1395 | David Bowie in Jazz (A Jazz Tribute to David Bowie) | Various Artists | `` | **Other / Unclassified** | `0.0` |
| 1396 | Way Out West (Deluxe Edition) | Sonny Rollins | `hard bop, jazz, bebop, jazz ballads, cool jazz, free jazz` | **Jazz** | `0.762` |
| 1397 | In New York [Original Jazz Classics Remasters] | Chet Baker | `jazz, cool jazz, vocal jazz, jazz ballads` | **Jazz** | `0.697` |
| 1398 | In These Times | Makaya McCraven | `nu jazz, experimental jazz, indie jazz, jazz, free jazz` | **Jazz** | `0.787` |
| 1399 | Trust In The Lifeforce Of The Deep Mystery | The Comet Is Coming | `nu jazz, experimental jazz, indie jazz, jazz fusion` | **Jazz** | `0.757` |
| 1400 | The Last Sound On Earth | Helado Negro | `latin alternative, latin indie` | **Latin / World** | `0.596` |
| 1401 | World Psychedelic Classics 5: Who Is William Onyeabor? | William Onyeabor | `afrobeat` | **Latin / World** | `0.508` |
| 1402 | La Danza de los Mirlos | Afrosound | `música tropical, cumbia, chicha, electrocumbia, merengue` | **Latin / World** | `0.552` |
| 1403 | Afrobeat Makers (Tony Allen Rhythms Revisited) | Tony Allen | `afrobeat` | **Latin / World** | `0.508` |
| 1404 | Private Energy | Helado Negro | `latin alternative, latin indie` | **Latin / World** | `0.596` |
| 1405 | LA BOA MEETS TONY ALLEN | Tony Allen | `afrobeat` | **Latin / World** | `0.508` |
| 1406 | Stop The Hate | Femi Kuti | `afrobeat, afropop, highlife` | **R&B / Soul** | `0.617` |
| 1407 | A Tribute To Art Blakey And The Jazz Messengers | Tony Allen | `afrobeat` | **Latin / World** | `0.508` |
| 1408 | Acabou Chorare | Novos Baianos | `mpb, samba, bossa nova` | **Latin / World** | `0.432` |
| 1409 | Ka Rica-Tar | Karl Hector & The Malcouns | `afrobeat, neo-psychedelic` | **Rock** | `0.533` |
| 1410 | PHASOR | Helado Negro | `latin alternative, latin indie` | **Latin / World** | `0.596` |
| 1411 | Rejoice (Special Edition) | Tony Allen | `afrobeat` | **Latin / World** | `0.508` |
| 1412 | Far In | Helado Negro | `latin alternative, latin indie` | **Latin / World** | `0.596` |
| 1413 | Uyai | Ibibio Sound Machine | `afrobeat` | **Latin / World** | `0.508` |
| 1414 | The Other Side | Seu Jorge | `mpb, samba, pagode` | **Latin / World** | `0.242` |
| 1415 | Ranil y su Conjunto Tropical | Ranil | `chicha, cumbia` | **Latin / World** | `0.224` |
| 1416 | The Source | Tony Allen | `afrobeat` | **Latin / World** | `0.508` |
| 1417 | Rejoice | Tony Allen | `afrobeat` | **Latin / World** | `0.508` |
| 1418 | Pareidolia Catalog, Vols. 5-8 | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1419 | L'un de nous | Albin de la Simone | `chanson, french pop, french indie pop` | **Pop** | `0.506` |
| 1420 | Sleepless Night | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1421 | Cap Waller | Bertrand Belin | `french pop, chanson, french indie pop` | **Pop** | `0.55` |
| 1422 | Super João | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1423 | Solide Mirage | Frànçois & The Atlas Mountains | `french indie pop, french pop` | **Pop** | `0.601` |
| 1424 | Midnight Snack | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1425 | La symphonie des éclairs | Zaho de Sagazan | `french pop, chanson, variété française` | **Pop** | `0.395` |
| 1426 | Waiting for the Phone to Ring | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1427 | Ouh là là | Juniore | `french indie pop, french pop` | **Pop** | `0.601` |
| 1428 | First Thought Best Thought | Arthur Russell | `art pop` | **Pop** | `0.549` |
| 1429 | Watt | Bertrand Belin | `french pop, chanson, french indie pop` | **Pop** | `0.55` |
| 1430 | Yours Sincerely | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 1431 | Halage | Frànçois & The Atlas Mountains | `french indie pop, french pop` | **Pop** | `0.601` |
| 1432 | La symphonie des éclairs (Orchestral Odyssey) | Zaho de Sagazan | `french pop, chanson, variété française` | **Pop** | `0.395` |
| 1433 | Sidération | Holden | `french indie pop, french pop` | **Pop** | `0.601` |
| 1434 | Cool Your Heart (Remixes) | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1435 | Empty Lot | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1436 | Gem | U.S. Girls | `art pop` | **Pop** | `0.549` |
| 1437 | -io | Circuit des Yeux | `slowcore, art pop` | **Pop** | `0.5` |
| 1438 | Tambour Vision (Nouvelle édition) | Bertrand Belin | `french pop, chanson, french indie pop` | **Pop** | `0.55` |
| 1439 | Haircut | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1440 | Remembering Me | Cate Le Bon | `art pop` | **Pop** | `0.549` |
| 1441 | The Bunker Sessions | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1442 | Pareidolia Catalog, Vols. 1-4 | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1443 | Distant Call - Collected Demos 2000 - 2006 | Broadcast | `dream pop, neo-psychedelic` | **Pop** | `0.503` |
| 1444 | 細野晴臣アーカイヴス Vol.1 | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 1445 | 万引き家族「オリジナル・サウンドトラック」 | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 1446 | Banane Bleue | Frànçois & The Atlas Mountains | `french indie pop, french pop` | **Pop** | `0.601` |
| 1447 | HOCHONO HOUSE | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 1448 | Trois, Deux, Un | Juniore | `french indie pop, french pop` | **Pop** | `0.601` |
| 1449 | Magic Sign | Martin Courtney | `jangle pop` | **Pop** | `0.298` |
| 1450 | Un homme | Albin de la Simone | `chanson, french pop, french indie pop` | **Pop** | `0.506` |
| 1451 | PARANOÏA, ANGELS, TRUE LOVE | Christine and the Queens | `art pop, french pop` | **Pop** | `0.555` |
| 1452 | Her River Raves Recollections | Frànçois & The Atlas Mountains | `french indie pop, french pop` | **Pop** | `0.601` |
| 1453 | Microtronics - Volumes 1 & 2 | Broadcast | `dream pop, neo-psychedelic` | **Pop** | `0.503` |
| 1454 | Nootropics Remixed | Lower Dens | `dream pop` | **Pop** | `0.472` |
| 1455 | Futurisme | Chevalrex | `french pop, french indie pop` | **Pop** | `0.592` |
| 1456 | Horsie (Deluxe) | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1457 | Undercurrent | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 1458 | Blueberry Boat (2025 Reissue) | The Fiery Furnaces | `art pop` | **Pop** | `0.549` |
| 1459 | Âge Fleuve | Frànçois & The Atlas Mountains | `french indie pop, french pop` | **Pop** | `0.601` |
| 1460 | Let's Change The World With Music | Prefab Sprout | `jangle pop` | **Pop** | `0.298` |
| 1461 | Andromeda Heights | Prefab Sprout | `jangle pop` | **Pop** | `0.298` |
| 1462 | Eighth | Eleventh Dream Day | `jangle pop, power pop` | **Pop** | `0.308` |
| 1463 | Genius + Love = Yo La Tengo | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1464 | The World Won'T End | Pernice Brothers | `power pop, jangle pop` | **Pop** | `0.319` |
| 1465 | The Hit Parade | The Wedding Present | `jangle pop, madchester` | **Pop** | `0.345` |
| 1466 | Arca | Arca | `neoperreo, experimental, art pop, hyperpop` | **Pop** | `0.496` |
| 1467 | Song of the Earth (Instrumentals) | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1468 | Hosono House | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 1469 | Truckload of Trouble | The Pastels | `jangle pop` | **Pop** | `0.298` |
| 1470 | Creatures of an Hour | Still Corners | `dream pop` | **Pop** | `0.472` |
| 1471 | Hosono House Revisited | Haruomi Hosono | `city pop, shibuya-kei` | **Pop** | `0.367` |
| 1472 | Calling From A Country Phone | Robert Forster | `jangle pop` | **Pop** | `0.298` |
| 1473 | Birkin / Gainsbourg : Le symphonique | Jane Birkin | `chanson, french pop, variété française` | **Reggae / Dub** | `0.37` |
| 1474 | Brol | Angèle | `french pop, variété française, chanson, french indie pop` | **Pop** | `0.541` |
| 1475 | Binary Childhood | Otzeki | `` | **Other / Unclassified** | `0.0` |
| 1476 | Exciting Times | Michelle Gurevich | `slowcore` | **Other / Unclassified** | `0.29` |
| 1477 | Good Time/Hard Time (Deluxe) | Teleman | `` | **Other / Unclassified** | `0.0` |
| 1478 | ABOMINATION | Lynks | `ballroom vogue` | **Other / Unclassified** | `0.308` |
| 1479 | Everybody Works | Jay Som | `dream pop, indie pop` | **Pop** | `0.666` |
| 1480 | We Come from the Same Place | Allo Darlin' | `jangle pop` | **Pop** | `0.298` |
| 1481 | The Caretaker | Half Waif | `art pop` | **Pop** | `0.549` |
| 1482 | The Last Exit | Still Corners | `dream pop` | **Pop** | `0.472` |
| 1483 | Belong | Jay Som | `dream pop, indie pop` | **Pop** | `0.666` |
| 1484 | Many Moons | Martin Courtney | `jangle pop` | **Pop** | `0.298` |
| 1485 | It's Art Dad | The Clientele | `dream pop, jangle pop` | **Pop** | `0.406` |
| 1486 | B-Sides and Rarities | Beach House | `dream pop` | **Pop** | `0.472` |
| 1487 | Mozart's Mini-Mart | Go-Kart Mozart | `jangle pop, go-go` | **Pop** | `0.324` |
| 1488 | I Am Not There Anymore | The Clientele | `dream pop, jangle pop` | **Pop** | `0.406` |
| 1489 | I Love You Jennifer B | Jockstrap | `art pop` | **Pop** | `0.549` |
| 1490 | Slow Air | Still Corners | `dream pop` | **Pop** | `0.472` |
| 1491 | Ego Death At A Bachelorette Party | Hayley Williams | `art pop` | **Pop** | `0.549` |
| 1492 | Heavy Light | U.S. Girls | `art pop` | **Pop** | `0.549` |
| 1493 | We Have Amnesia Sometimes | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1494 | Plaza | Quilt | `neo-psychedelic, retro pop` | **Pop** | `0.519` |
| 1495 | And Then Nothing Turned Itself Inside-Out | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1496 | I Killed Your Dog | L'Rain | `neo-psychedelic, art pop` | **Pop** | `0.564` |
| 1497 | Breakfast | Teleman | `` | **Other / Unclassified** | `0.0` |
| 1498 | Chaleur Humaine | Christine and the Queens | `art pop, french pop` | **Pop** | `0.555` |
| 1499 | Lives | U.S. Girls | `art pop` | **Pop** | `0.549` |
| 1500 | Fetch The Bolt Cutters | Fiona Apple | `art pop` | **Pop** | `0.549` |
| 1501 | Cupid Deluxe | Blood Orange | `art pop` | **Pop** | `0.549` |
| 1502 | Sideways to New Italy | Rolling Blackouts Coastal Fever | `jangle pop` | **Pop** | `0.298` |
| 1503 | Endless Rooms | Rolling Blackouts Coastal Fever | `jangle pop` | **Pop** | `0.298` |
| 1504 | Thank Your Lucky Stars | Beach House | `dream pop` | **Pop** | `0.472` |
| 1505 | I Can Hear The Heart Beating As One | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1506 | Mount Wittenberg Orca | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1507 | The Noise Made By People | Broadcast | `dream pop, neo-psychedelic` | **Pop** | `0.503` |
| 1508 | No Shape | Perfume Genius | `art pop` | **Pop** | `0.549` |
| 1509 | Blood Bitch | Jenny Hval | `art pop` | **Pop** | `0.549` |
| 1510 | Hope Downs | Rolling Blackouts Coastal Fever | `jangle pop` | **Pop** | `0.298` |
| 1511 | Radiate Like This | Warpaint | `dream pop` | **Pop** | `0.472` |
| 1512 | fata morgana | L'Rain | `neo-psychedelic, art pop` | **Pop** | `0.564` |
| 1513 | Heartworms | The Shins | `indie, indie pop` | **Pop** | `0.72` |
| 1514 | Essex Honey | Blood Orange | `art pop` | **Pop** | `0.549` |
| 1515 | 5EPs | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1516 | There's a Riot Going On | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1517 | Tender Buttons | Broadcast | `dream pop, neo-psychedelic` | **Pop** | `0.503` |
| 1518 | Crimson/Red | Prefab Sprout | `jangle pop` | **Pop** | `0.298` |
| 1519 | Anak Ko | Jay Som | `dream pop, indie pop` | **Pop** | `0.666` |
| 1520 | The Sounds of the Sounds of Science | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1521 | Look to the East, Look to the West | Camera Obscura | `indie pop, jangle pop` | **Pop** | `0.629` |
| 1522 | Music for People in Trouble | Susanne Sundfør | `norwegian pop, art pop` | **Pop** | `0.526` |
| 1523 | BRAT | Charli xcx | `hyperpop, art pop` | **Pop** | `0.461` |
| 1524 | Once Twice Melody | Beach House | `dream pop` | **Pop** | `0.472` |
| 1525 | Broadcast And The Focus Group Investigate Witch Cults Of The Radio Age | Broadcast | `dream pop, neo-psychedelic` | **Pop** | `0.503` |
| 1526 | Pompeii | Cate Le Bon | `art pop` | **Pop** | `0.549` |
| 1527 | Michelangelo Dying | Cate Le Bon | `art pop` | **Pop** | `0.549` |
| 1528 | 22, A Million | Bon Iver | `` | **Other / Unclassified** | `0.0` |
| 1529 | Calling Out Of Context | Arthur Russell | `art pop` | **Pop** | `0.549` |
| 1530 | This Stupid World | Yo La Tengo | `dream pop, slowcore` | **Pop** | `0.462` |
| 1531 | Fresh Air | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1532 | Desire, I Want To Turn Into You | Caroline Polachek | `art pop` | **Pop** | `0.549` |
| 1533 | This Is How You Smile | Helado Negro | `latin alternative, latin indie` | **Latin / World** | `0.596` |
| 1534 | Soon Over Babluma (Remastered) | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1535 | New Heart Designs | Turnstile | `hardcore punk, hardcore` | **Punk / Alternative** | `0.616` |
| 1536 | #7885 (Electropunk to Technopop 1978-1985) | Cabaret Voltaire | `industrial, ebm, post-punk, synthpop, industrial rock, experimental, cold wave, new wave, avant-garde, darkwave, krautrock` | **Punk / Alternative** | `0.773` |
| 1537 | Come Play the Trees | Snapped Ankles | `post-punk, krautrock, space rock` | **Punk / Alternative** | `0.694` |
| 1538 | Still There’s a Glow | Sweet Pill | `midwest emo, math rock` | **Punk / Alternative** | `0.555` |
| 1539 | Around | Tom Verlaine | `proto-punk, post-punk, art rock` | **Punk / Alternative** | `0.745` |
| 1540 | Stay Safe! | La Sécurité | `egg punk, rock québécois` | **Punk / Alternative** | `0.411` |
| 1541 | Post Pop Depression | Iggy Pop | `proto-punk, glam rock` | **Punk / Alternative** | `0.623` |
| 1542 | MiXology (volume 1) | John Cale | `art rock, baroque pop, proto-punk, singer-songwriter` | **Pop** | `0.677` |
| 1543 | WIRED | Basement | `midwest emo, shoegaze` | **Punk / Alternative** | `0.365` |
| 1544 | Bingo! | La Sécurité | `egg punk, rock québécois` | **Punk / Alternative** | `0.411` |
| 1545 | LIVE IN ASTON 1977 | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1546 | Good Living Is Coming For You | Sweeping Promises | `egg punk, post-punk` | **Punk / Alternative** | `0.551` |
| 1547 | Sublime (10th Anniversary Edition / Deluxe Edition) | Sublime | `reggae rock, ska punk, ska` | **Reggae / Dub** | `0.759` |
| 1548 | Future Days (Remastered) | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1549 | We Can Do Anything | Violent Femmes | `folk punk` | **Punk / Alternative** | `0.599` |
| 1550 | LIVE IN CUXHAVEN 1976 | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1551 | Transformer | Lou Reed | `glam rock, proto-punk, art rock` | **Punk / Alternative** | `0.741` |
| 1552 | Crumbling the Antiseptic Beauty (Remastered Edition) | Felt | `jangle pop, post-punk` | **Punk / Alternative** | `0.537` |
| 1553 | Vini Reilly | The Durutti Column | `madchester, art rock, post-punk` | **Punk / Alternative** | `0.625` |
| 1554 | Unlimited Edition (Remastered) | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1555 | In the Aeroplane Over the Sea | Neutral Milk Hotel | `anti-folk, folk punk` | **Punk / Alternative** | `0.533` |
| 1556 | Hot Potatoes: The Best Of Devo | DEVO | `new wave, post-punk, synthpop` | **Punk / Alternative** | `0.669` |
| 1557 | The Holy Cross Tigers | Twisted Teens | `` | **Other / Unclassified** | `0.0` |
| 1558 | Sun Coming Down | Ought | `post-punk` | **Punk / Alternative** | `0.601` |
| 1559 | EVERY LOSER | Iggy Pop | `proto-punk, glam rock` | **Punk / Alternative** | `0.623` |
| 1560 | New Long Leg | Dry Cleaning | `post-punk, spoken word` | **Punk / Alternative** | `0.539` |
| 1561 | Set the Twilight Reeling | Lou Reed | `glam rock, proto-punk, art rock` | **Punk / Alternative** | `0.741` |
| 1562 | All Nerve | The Breeders | `riot grrrl, alternative rock` | **Punk / Alternative** | `0.569` |
| 1563 | Magic and Loss | Lou Reed | `glam rock, proto-punk, art rock` | **Punk / Alternative** | `0.741` |
| 1564 | Free | Iggy Pop | `proto-punk, glam rock` | **Punk / Alternative** | `0.623` |
| 1565 | New York | Lou Reed | `glam rock, proto-punk, art rock` | **Punk / Alternative** | `0.741` |
| 1566 | Deep in View | Cola | `post-punk, egg punk` | **Punk / Alternative** | `0.557` |
| 1567 | Ritual De Lo Habitual | Jane's Addiction | `funk rock, grunge` | **Punk / Alternative** | `0.637` |
| 1568 | Seventeen Seconds | The Cure | `new wave, post-punk, gothic rock, darkwave` | **Punk / Alternative** | `0.733` |
| 1569 | Songs For Drella | Lou Reed | `glam rock, proto-punk, art rock` | **Punk / Alternative** | `0.741` |
| 1570 | Secret Love | Dry Cleaning | `post-punk, spoken word` | **Punk / Alternative** | `0.539` |
| 1571 | Women | Women | `noise rock, post-punk` | **Punk / Alternative** | `0.699` |
| 1572 | Tago Mago (40th Anniversary Edition) | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1573 | Ege Bamyasi (Remastered) | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1574 | Bright Green Field | Squid | `post-punk, art rock, noise rock` | **Punk / Alternative** | `0.785` |
| 1575 | Final Summer | Cloud Nothings | `indie punk, garage rock, noise rock` | **Punk / Alternative** | `0.719` |
| 1576 | Relatives In Descent | Protomartyr | `post-punk, noise rock, indie punk` | **Punk / Alternative** | `0.783` |
| 1577 | Zombie Birdhouse | Iggy Pop | `proto-punk, glam rock` | **Punk / Alternative** | `0.623` |
| 1578 | The Underside of Power | Algiers | `post-punk` | **Punk / Alternative** | `0.601` |
| 1579 | The Singles | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1580 | NEVER ENOUGH | Turnstile | `hardcore punk, hardcore` | **Punk / Alternative** | `0.616` |
| 1581 | POPtical Illusion | John Cale | `art rock, baroque pop, proto-punk, singer-songwriter` | **Pop** | `0.677` |
| 1582 | Comfort To Me | Amyl and The Sniffers | `riot grrrl, punk` | **Punk / Alternative** | `0.455` |
| 1583 | Porno For Pyros | Porno for Pyros | `funk rock, grunge` | **Punk / Alternative** | `0.637` |
| 1584 | Renascent | The Durutti Column | `madchester, art rock, post-punk` | **Punk / Alternative** | `0.625` |
| 1585 | GLOW ON | Turnstile | `hardcore punk, hardcore` | **Punk / Alternative** | `0.616` |
| 1586 | viagr aboys | Viagra Boys | `post-punk, egg punk` | **Punk / Alternative** | `0.557` |
| 1587 | Three Imaginary Boys | The Cure | `new wave, post-punk, gothic rock, darkwave` | **Punk / Alternative** | `0.733` |
| 1588 | Teens of Denial | Car Seat Headrest | `midwest emo, indie rock` | **Punk / Alternative** | `0.641` |
| 1589 | Tin Drum | Japan | `new wave, synthpop, post-punk, art pop` | **Pop** | `0.729` |
| 1590 | Songs Of A Lost World | The Cure | `new wave, post-punk, gothic rock, darkwave` | **Punk / Alternative** | `0.733` |
| 1591 | Marauder | Interpol | `indie rock, post-punk` | **Punk / Alternative** | `0.726` |
| 1592 | Stumpwork | Dry Cleaning | `post-punk, spoken word` | **Punk / Alternative** | `0.539` |
| 1593 | Formal Growth In The Desert | Protomartyr | `post-punk, noise rock, indie punk` | **Punk / Alternative** | `0.783` |
| 1594 | Ecstasy | Lou Reed | `glam rock, proto-punk, art rock` | **Punk / Alternative** | `0.741` |
| 1595 | Adore Life | Savages | `post-punk` | **Punk / Alternative** | `0.601` |
| 1596 | Faith | The Cure | `new wave, post-punk, gothic rock, darkwave` | **Punk / Alternative** | `0.733` |
| 1597 | I Used to Spend So Much Time Alone | Chastity Belt | `indie punk` | **Punk / Alternative** | `0.655` |
| 1598 | LIVE IN BRIGHTON 1975 | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1599 | This Mirror Weighs a Ton | Interpol | `indie rock, post-punk` | **Punk / Alternative** | `0.726` |
| 1600 | All Clouds Bring Not Rain | MEMORIALS | `neo-psychedelic, egg punk` | **Punk / Alternative** | `0.443` |
| 1601 | Preoccupations | Preoccupations | `post-punk, noise rock, cold wave` | **Punk / Alternative** | `0.715` |
| 1602 | Twenty Odd Years | Subway Sect | `post-punk, proto-punk, new wave, punk` | **Punk / Alternative** | `0.723` |
| 1603 | LIVE IN ARLES 1975 | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1604 | Saw Delight (Remastered) | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1605 | Kitchen Sink | Nadine Shah | `art rock` | **Rock** | `0.563` |
| 1606 | LIVE IN PARIS 1973 | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1607 | Wide Awake! | Parquet Courts | `indie rock, post-punk, garage rock` | **Punk / Alternative** | `0.733` |
| 1608 | LIVE IN STUTTGART 1975 | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1609 | Skylarking | XTC | `new wave, power pop, post-punk, jangle pop` | **Punk / Alternative** | `0.642` |
| 1610 | Human Performance | Parquet Courts | `indie rock, post-punk, garage rock` | **Punk / Alternative** | `0.733` |
| 1611 | I Got Heaven | Mannequin Pussy | `riot grrrl, queercore, indie punk` | **Punk / Alternative** | `0.647` |
| 1612 | Romance | Fontaines D.C. | `post-punk` | **Punk / Alternative** | `0.601` |
| 1613 | The Other Side Of Make-Believe | Interpol | `indie rock, post-punk` | **Punk / Alternative** | `0.726` |
| 1614 | It's a Beautiful Place | Water From Your Eyes | `` | **Other / Unclassified** | `0.0` |
| 1615 | Dopamine Chamber | Fontaines D.C. | `post-punk` | **Punk / Alternative** | `0.601` |
| 1616 | Public Strain | Women | `noise rock, post-punk` | **Punk / Alternative** | `0.699` |
| 1617 | HELLMODE | Jeff Rosenstock | `folk punk, indie punk, power pop` | **Punk / Alternative** | `0.682` |
| 1618 | Bedroom | bdrmm | `shoegaze, lo-fi indie, dream pop, post-punk` | **Rock** | `0.728` |
| 1619 | The Lost Tapes | CAN | `krautrock, space rock, progressive rock, psychedelic rock, experimental, art rock, proto-punk` | **Rock** | `0.804` |
| 1620 | Homegrown | CARRTOONS | `retro soul` | **R&B / Soul** | `0.389` |
| 1621 | Cyan Blue | Charlotte Day Wilson | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1622 | Slow Burn | Baby Rose | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1623 | Small Things | Nick Hakim | `indie soul` | **Rock** | `0.594` |
| 1624 | Live At The Roundhouse | Lianne La Havas | `alternative r&b, soul, pop soul, neo soul` | **R&B / Soul** | `0.642` |
| 1625 | Saturday Night | CARRTOONS | `retro soul` | **R&B / Soul** | `0.389` |
| 1626 | COMETA | Nick Hakim | `indie soul` | **Rock** | `0.594` |
| 1627 | Stone Woman | Charlotte Day Wilson | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1628 | Green Twins | Nick Hakim | `indie soul` | **Rock** | `0.594` |
| 1629 | there's an atm inside | ps goner | `bedroom pop, alternative r&b` | **R&B / Soul** | `0.382` |
| 1630 | Where Will We Go, Pt. 2 | Nick Hakim | `indie soul` | **Rock** | `0.594` |
| 1631 | Where Will We Go, Pt. 1 | Nick Hakim | `indie soul` | **Rock** | `0.594` |
| 1632 | CDW | Charlotte Day Wilson | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1633 | Yatta! | Yin Yin | `` | **Other / Unclassified** | `0.0` |
| 1634 | Renascence | Cymande | `funk, afrobeat` | **R&B / Soul** | `0.627` |
| 1635 | Illusions | Menahan Street Band | `retro soul` | **R&B / Soul** | `0.389` |
| 1636 | The Exciting Sounds of Menahan Street Band | Menahan Street Band | `retro soul` | **R&B / Soul** | `0.389` |
| 1637 | First Take (Deluxe Edition) | Roberta Flack | `adult standards, classic soul` | **R&B / Soul** | `0.265` |
| 1638 | Lianne La Havas | Lianne La Havas | `alternative r&b, soul, pop soul, neo soul` | **R&B / Soul** | `0.642` |
| 1639 | Sudan Archives | Sudan Archives | `alternative r&b, indie soul` | **R&B / Soul** | `0.626` |
| 1640 | trip9love...??? | Tirzah | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1641 | Under The Weather | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1642 | Doctrine of Love | Jalen Ngonda | `retro soul` | **R&B / Soul** | `0.389` |
| 1643 | Sauropoda | L'Eclair | `` | **Other / Unclassified** | `0.0` |
| 1644 | The Age of Pleasure | Janelle Monáe | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1645 | Colourgrade | Tirzah | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1646 | Make the Road By Walking | Menahan Street Band | `retro soul` | **R&B / Soul** | `0.389` |
| 1647 | THE BPM | Sudan Archives | `alternative r&b, indie soul` | **R&B / Soul** | `0.626` |
| 1648 | Lahai | Sampha | `indie soul` | **Rock** | `0.594` |
| 1649 | Honora | Flea | `funk rock` | **R&B / Soul** | `0.594` |
| 1650 | The Electric Lady | Janelle Monáe | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1651 | græ | Moses Sumney | `art pop, indie soul` | **Pop** | `0.689` |
| 1652 | WILL THIS MAKE ME GOOD | Nick Hakim | `indie soul` | **Rock** | `0.594` |
| 1653 | Room 25 | Noname | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1654 | Before The World Blows | Erykah Badu | `neo soul, r&b, alternative r&b` | **R&B / Soul** | `0.563` |
| 1655 | Ctrl | SZA | `r&b` | **R&B / Soul** | `0.382` |
| 1656 | KIWANUKA | Michael Kiwanuka | `soul` | **R&B / Soul** | `0.415` |
| 1657 | MAGDALENE | FKA twigs | `art pop, alternative r&b` | **Pop** | `0.529` |
| 1658 | Small Changes | Michael Kiwanuka | `soul` | **R&B / Soul** | `0.415` |
| 1659 | CAPRISONGS | FKA twigs | `art pop, alternative r&b` | **Pop** | `0.529` |
| 1660 | Skin | Joy Crookes | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1661 | Love & Hate | Michael Kiwanuka | `soul` | **R&B / Soul** | `0.415` |
| 1662 | Baby | Dijon | `` | **Other / Unclassified** | `0.0` |
| 1663 | Untitled (God) | SAULT | `` | **Other / Unclassified** | `0.0` |
| 1664 | Process | Sampha | `indie soul` | **Rock** | `0.594` |
| 1665 | Heavy Metal | Cameron Winter | `` | **Other / Unclassified** | `0.0` |
| 1666 | The Colour In Anything | James Blake | `` | **Other / Unclassified** | `0.0` |
| 1667 | Fatigue | L'Rain | `neo-psychedelic, art pop` | **Pop** | `0.564` |
| 1668 | Self Help | Badge Époque Ensemble | `` | **Other / Unclassified** | `0.0` |
| 1669 | ALPHA | Charlotte Day Wilson | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1670 | Gemini Rights | Steve Lacy | `` | **Other / Unclassified** | `0.0` |
| 1671 | Take Me Apart | Kelela | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1672 | Dirty Computer | Janelle Monáe | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1673 | Helium | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1674 | Devotion | Tirzah | `alternative r&b` | **R&B / Soul** | `0.352` |
| 1675 | A Seat at the Table | Solange | `alternative r&b, neo soul` | **R&B / Soul** | `0.534` |
| 1676 | Station to Station (1999 Remaster) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1677 | Friends That Break Your Heart | James Blake | `` | **Other / Unclassified** | `0.0` |
| 1678 | Aquarius Dub | Herman Chin Loy | `dub, rocksteady, roots reggae` | **Reggae / Dub** | `0.679` |
| 1679 | A Trip To Bolgatanga | African Head Charge | `dub, space rock` | **Reggae / Dub** | `0.414` |
| 1680 | Midnight Rocker | Horace Andy | `roots reggae, dub, reggae, rocksteady, lovers rock, ragga` | **Reggae / Dub** | `0.764` |
| 1681 | Reggae Greats | Steel Pulse | `reggae, roots reggae, ragga, rocksteady, dub` | **Reggae / Dub** | `0.769` |
| 1682 | Isn’t It Now? | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1683 | Melodi | Kit Sebastian | `anatolian rock` | **Rock** | `0.292` |
| 1684 | ZIRP! | DIIV | `` | **Other / Unclassified** | `0.0` |
| 1685 | Petition / My Better Self | Tennis | `` | **Other / Unclassified** | `0.0` |
| 1686 | The True Story of Bananagun | Bananagun (Aus) | `neo-psychedelic, psychedelic rock` | **Rock** | `0.561` |
| 1687 | Vol.II | Angine de Poitrine | `math rock` | **Rock** | `0.443` |
| 1688 | Wilderness | Archer Prewitt | `post-rock, slowcore` | **Rock** | `0.507` |
| 1689 | Unfold | Melody's Echo Chamber | `neo-psychedelic, dream pop, psychedelic rock` | **Rock** | `0.643` |
| 1690 | Love Chant | The Lemonheads | `power pop, alternative rock` | **Rock** | `0.607` |
| 1691 | The Wee Small Hours: B-Sides and Other Detritus 2011-2025 | Real Estate | `jangle pop, dream pop, surf rock` | **Rock** | `0.519` |
| 1692 | Open Close | Sam Prekop | `post-rock` | **Rock** | `0.494` |
| 1693 | Crestone (Original Score) | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1694 | Ecstatic Arrow | Virginia Wing | `space rock, art pop` | **Pop** | `0.595` |
| 1695 | Spotify Sessions | Real Estate | `jangle pop, dream pop, surf rock` | **Rock** | `0.519` |
| 1696 | Laughing Gas | Wild Nothing | `dream pop, shoegaze, chillwave` | **Rock** | `0.532` |
| 1697 | Rot | Conrad Schnitzler | `krautrock, space rock, musique concrète, avant-garde, experimental` | **Rock** | `0.614` |
| 1698 | >>> | Beak> | `krautrock, space rock, neo-psychedelic` | **Rock** | `0.623` |
| 1699 | Teach Me to Forget | The Radio Dept. | `dream pop, shoegaze` | **Rock** | `0.412` |
| 1700 | Half a Human | Real Estate | `jangle pop, dream pop, surf rock` | **Rock** | `0.519` |
| 1701 | Serkut rakastaa paremmin | Tv-Resistori | `finnish rock, finnish pop` | **Pop** | `0.483` |
| 1702 | Comma | Sam Prekop | `post-rock` | **Rock** | `0.494` |
| 1703 | Ballads of Harry Houdini | Papa M | `slowcore, post-rock` | **Rock** | `0.516` |
| 1704 | West End Coast | Young Gun Silver Fox | `yacht rock, aor` | **Rock** | `0.323` |
| 1705 | OUTTANATIONAL | Pigeon | `` | **Other / Unclassified** | `0.0` |
| 1706 | This Way Out | Idaho | `slowcore` | **Other / Unclassified** | `0.29` |
| 1707 | Play What They Want | Man Forever | `space rock` | **Rock** | `0.419` |
| 1708 | Flight Tower | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1709 | On Grace & Dignity | The Golden Dregs | `` | **Other / Unclassified** | `0.0` |
| 1710 | Watering The Valley | Big Warm Bed | `` | **Other / Unclassified** | `0.0` |
| 1711 | Persona | Bertrand Belin | `french pop, chanson, french indie pop` | **Pop** | `0.55` |
| 1712 | Thanatos | Atlas Sound | `dream pop, neo-psychedelic, shoegaze` | **Rock** | `0.58` |
| 1713 | Mark Hollis | Mark Hollis | `post-rock, art rock` | **Rock** | `0.598` |
| 1714 | Christmas | Low | `slowcore, dream pop, post-rock` | **Rock** | `0.633` |
| 1715 | caroline | caroline | `slowcore, post-rock` | **Rock** | `0.516` |
| 1716 | People | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1717 | 12 X 5 | The Rolling Stones | `classic rock, rock` | **Rock** | `0.603` |
| 1718 | Animals (2011 Remastered Version) | Pink Floyd | `progressive rock, psychedelic rock, classic rock, art rock, rock` | **Rock** | `0.864` |
| 1719 | Mirror Repair | Gastr Del Sol | `post-rock, math rock, slowcore` | **Rock** | `0.597` |
| 1720 | Norther | Ex-Easter Island Head | `electroacoustic, space rock` | **Rock** | `0.331` |
| 1721 | Stage (Live; 2005 Remaster) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1722 | Inní | Sigur Rós | `post-rock, dream pop` | **Rock** | `0.618` |
| 1723 | Unclouded | Melody's Echo Chamber | `neo-psychedelic, dream pop, psychedelic rock` | **Rock** | `0.643` |
| 1724 | Sue (Or in a Season of Crime) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1725 | I Love You, Honeybear Demos, etc. | Father John Misty | `` | **Other / Unclassified** | `0.0` |
| 1726 | circle the drain | Soccer Mommy | `indie` | **Pop** | `0.591` |
| 1727 | City to City | Gerry Rafferty | `yacht rock` | **Rock** | `0.413` |
| 1728 | Live at 9:30 | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1729 | In the Sun | Archer Prewitt | `post-rock, slowcore` | **Rock** | `0.507` |
| 1730 | The Inspection (Original Motion Picture Soundtrack) | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1731 | Snow Borne Sorrow | Nine Horses | `art rock, art pop` | **Pop** | `0.642` |
| 1732 | Spirit They're Gone, Spirit They've Vanished (Remastered 2023) | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1733 | Influences | K.D.A.P. | `` | **Other / Unclassified** | `0.0` |
| 1734 | The Candle and the Flame | Robert Forster | `jangle pop` | **Pop** | `0.298` |
| 1735 | Foreign Spies / Zero Sum | The Smile | `art rock` | **Rock** | `0.563` |
| 1736 | I Was Real | 75 Dollar Bill | `space rock` | **Rock** | `0.419` |
| 1737 | Metrobolist (aka The Man Who Sold The World) [2020 Mix] | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1738 | Wish You Were Here (2011 Remastered Version) | Pink Floyd | `progressive rock, psychedelic rock, classic rock, art rock, rock` | **Rock** | `0.864` |
| 1739 | The Perfect Prescription | Spacemen 3 | `space rock, neo-psychedelic, shoegaze, psychedelic rock, dream pop` | **Rock** | `0.759` |
| 1740 | Spooky | Lush | `shoegaze, dream pop, britpop, slowcore` | **Rock** | `0.544` |
| 1741 | One Bedroom | The Sea and Cake | `post-rock` | **Rock** | `0.494` |
| 1742 | First Two Pages of Frankenstein | The National | `indie rock` | **Rock** | `0.735` |
| 1743 | Sleep Well Beast | The National | `indie rock` | **Rock** | `0.735` |
| 1744 | I Can't Give Everything Away E.P | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1745 | Scary Monsters | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1746 | Ash & Ice | The Kills | `garage rock` | **Rock** | `0.488` |
| 1747 | Camoufleur | Gastr Del Sol | `post-rock, math rock, slowcore` | **Rock** | `0.597` |
| 1748 | Beacons of Ancestorship | Tortoise | `post-rock, math rock, krautrock, slowcore` | **Rock** | `0.613` |
| 1749 | Indigo | Wild Nothing | `dream pop, shoegaze, chillwave` | **Rock** | `0.532` |
| 1750 | Blue Rev | Alvvays | `dream pop, shoegaze, jangle pop, indie` | **Pop** | `0.668` |
| 1751 | A Promise | Xiu Xiu | `art pop, noise rock` | **Pop** | `0.636` |
| 1752 | Touch | Tortoise | `post-rock, math rock, krautrock, slowcore` | **Rock** | `0.613` |
| 1753 | In The Morse Code Of Brake Lights | The New Pornographers | `power pop, indie rock, indie` | **Pop** | `0.735` |
| 1754 | Antisocialites | Alvvays | `dream pop, shoegaze, jangle pop, indie` | **Pop** | `0.668` |
| 1755 | It's All Around You | Tortoise | `post-rock, math rock, krautrock, slowcore` | **Rock** | `0.613` |
| 1756 | Atlas | Real Estate | `jangle pop, dream pop, surf rock` | **Rock** | `0.519` |
| 1757 | Y Dydd Olaf | Gwenno | `space rock` | **Rock** | `0.419` |
| 1758 | Wall Of Eyes | The Smile | `art rock` | **Rock** | `0.563` |
| 1759 | Lodger (1999 Remaster) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1760 | Let's Dance (1999 Remaster) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1761 | End of the Middle | Richard Dawson | `art rock` | **Rock** | `0.563` |
| 1762 | The Dark Side Of The Moon (2011 Remastered Version) | Pink Floyd | `progressive rock, psychedelic rock, classic rock, art rock, rock` | **Rock** | `0.864` |
| 1763 | Time Skiffs | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1764 | Car Alarm | The Sea and Cake | `post-rock` | **Rock** | `0.494` |
| 1765 | Sun and Shade | Woods | `neo-psychedelic, space rock` | **Rock** | `0.562` |
| 1766 | Holiday Destination | Nadine Shah | `art rock` | **Rock** | `0.563` |
| 1767 | Le Kov | Gwenno | `space rock` | **Rock** | `0.419` |
| 1768 | Old Ramon | Red House Painters | `slowcore, shoegaze` | **Rock** | `0.331` |
| 1769 | Rock Bottom | Robert Wyatt | `art rock, progressive rock, experimental, krautrock` | **Rock** | `0.673` |
| 1770 | What a Time to Be Alive | Superchunk | `power pop, indie rock, alternative rock` | **Rock** | `0.733` |
| 1771 | Automatic For The People (25th Anniversary Edition) | R.E.M. | `jangle pop, alternative rock, rock` | **Rock** | `0.621` |
| 1772 | The Next Day Extra EP | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1773 | Nothing Important | Richard Dawson | `art rock` | **Rock** | `0.563` |
| 1774 | Cutouts | The Smile | `art rock` | **Rock** | `0.563` |
| 1775 | No Home Record | Kim Gordon | `noise rock` | **Rock** | `0.496` |
| 1776 | Getting Killed | Geese | `art rock` | **Rock** | `0.563` |
| 1777 | Wincing the Night Away | The Shins | `indie, indie pop` | **Pop** | `0.72` |
| 1778 | Rock N Roll Consciousness | Thurston Moore | `noise rock` | **Rock** | `0.496` |
| 1779 | A New Career in a New Town (1977 - 1982) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1780 | In Mind | Real Estate | `jangle pop, dream pop, surf rock` | **Rock** | `0.519` |
| 1781 | Daniel | Real Estate | `jangle pop, dream pop, surf rock` | **Rock** | `0.519` |
| 1782 | Serfs Up! | Fat White Family | `space rock` | **Rock** | `0.419` |
| 1783 | Manafon | David Sylvian | `art pop, art rock` | **Pop** | `0.644` |
| 1784 | Life of Pause | Wild Nothing | `dream pop, shoegaze, chillwave` | **Rock** | `0.532` |
| 1785 | Bon Voyage | Melody's Echo Chamber | `neo-psychedelic, dream pop, psychedelic rock` | **Rock** | `0.643` |
| 1786 | HEY WHAT | Low | `slowcore, dream pop, post-rock` | **Rock** | `0.633` |
| 1787 | The Nightfly | Donald Fagen | `yacht rock, aor` | **Rock** | `0.323` |
| 1788 | Plays the Music of Twin Peaks | Xiu Xiu | `art pop, noise rock` | **Pop** | `0.636` |
| 1789 | Microshift | Hookworms | `neo-psychedelic, space rock, krautrock, psychedelic rock` | **Rock** | `0.675` |
| 1790 | Chemical Chords | Stereolab | `art pop, krautrock, neo-psychedelic, post-rock` | **Rock** | `0.734` |
| 1791 | In a Poem Unlimited | U.S. Girls | `art pop` | **Pop** | `0.549` |
| 1792 | Reset in Dub | Sonic Boom | `space rock, neo-psychedelic` | **Rock** | `0.586` |
| 1793 | Heroes (1999 Remaster) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1794 | Emotional Eternal | Melody's Echo Chamber | `neo-psychedelic, dream pop, psychedelic rock` | **Rock** | `0.643` |
| 1795 | United Kingdom | American Music Club | `slowcore` | **Other / Unclassified** | `0.29` |
| 1796 | The Ruby Cord | Richard Dawson | `art rock` | **Rock** | `0.563` |
| 1797 | The Collective | Kim Gordon | `noise rock` | **Rock** | `0.496` |
| 1798 | Merriweather Post Pavilion | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1799 | Double Negative | Low | `slowcore, dream pop, post-rock` | **Rock** | `0.633` |
| 1800 | Feels (20th Anniversary) | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1801 | Low (1999 Remaster) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1802 | Painting With | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1803 | 2020 | Richard Dawson | `art rock` | **Rock** | `0.563` |
| 1804 | Tangerine Reef | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1805 | Midnight Boom | The Kills | `garage rock` | **Rock** | `0.488` |
| 1806 | The Wilderness | Explosions In The Sky | `post-rock` | **Rock** | `0.494` |
| 1807 | Heaven or Las Vegas | Cocteau Twins | `dream pop, shoegaze` | **Rock** | `0.412` |
| 1808 | Any Day | The Sea and Cake | `post-rock` | **Rock** | `0.494` |
| 1809 | Strange to Explain | Woods | `neo-psychedelic, space rock` | **Rock** | `0.562` |
| 1810 | Logos | Atlas Sound | `dream pop, neo-psychedelic, shoegaze` | **Rock** | `0.58` |
| 1811 | Instant Holograms On Metal Film | Stereolab | `art pop, krautrock, neo-psychedelic, post-rock` | **Rock** | `0.734` |
| 1812 | Clash The Truth | Beach Fossils | `dream pop, surf rock, shoegaze` | **Rock** | `0.614` |
| 1813 | The Flower Lane | Ducktails | `` | **Other / Unclassified** | `0.0` |
| 1814 | Whiteout Conditions | The New Pornographers | `power pop, indie rock, indie` | **Pop** | `0.735` |
| 1815 | The Catastrophist | Tortoise | `post-rock, math rock, krautrock, slowcore` | **Rock** | `0.613` |
| 1816 | Home Video | Lucy Dacus | `` | **Other / Unclassified** | `0.0` |
| 1817 | caroline 2 | caroline | `slowcore, post-rock` | **Rock** | `0.516` |
| 1818 | A Light for Attracting Attention | The Smile | `art rock` | **Rock** | `0.563` |
| 1819 | The Car | Arctic Monkeys | `indie, garage rock` | **Rock** | `0.672` |
| 1820 | I Am Easy to Find | The National | `indie rock` | **Rock** | `0.735` |
| 1821 | Sung Tongs | Animal Collective | `neo-psychedelic, indie rock` | **Rock** | `0.686` |
| 1822 | Peasant | Richard Dawson | `art rock` | **Rock** | `0.563` |
| 1823 | Tresor | Gwenno | `space rock` | **Rock** | `0.419` |
| 1824 | The Dream | alt-J | `indie, indie rock` | **Rock** | `0.725` |
| 1825 | Who's Your New Professor | Sam Prekop | `post-rock` | **Rock** | `0.494` |
| 1826 | Is the Is Are | DIIV | `shoegaze, dream pop` | **Rock** | `0.403` |
| 1827 | This Is All Yours | alt-J | `indie, indie rock` | **Rock** | `0.725` |
| 1828 | Laugh Track | The National | `indie rock` | **Rock** | `0.735` |
| 1829 | The Ballad of Darren | Blur | `britpop, alternative rock` | **Punk / Alternative** | `0.559` |
| 1830 | Yerself Is Steam | Mercury Rev | `neo-psychedelic, shoegaze` | **Rock** | `0.473` |
| 1831 | Henki | Richard Dawson | `art rock` | **Rock** | `0.563` |
| 1832 | Escape From Evil | Lower Dens | `dream pop` | **Pop** | `0.472` |
| 1833 | David Bowie (Deluxe Edition) | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1834 | Mobile Home | Longpigs | `britpop, madchester` | **Pop** | `0.362` |
| 1835 | Flock | Jane Weaver | `space rock` | **Rock** | `0.419` |
| 1836 | Alvvays | Alvvays | `` | **Other / Unclassified** | `0.0` |
| 1837 | Reward | Cate Le Bon | `art pop` | **Pop** | `0.549` |
| 1838 | CD Wallet | HOMESHAKE | `bedroom pop` | **Pop** | `0.378` |
| 1839 | Sam Prekop | Sam Prekop | `post-rock` | **Rock** | `0.494` |
| 1840 | The OOZ | King Krule | `` | **Other / Unclassified** | `0.0` |
| 1841 | Old Rottenhat | Robert Wyatt | `art rock, progressive rock, experimental, krautrock` | **Rock** | `0.673` |
| 1842 | Slowdive | Slowdive | `shoegaze, dream pop, slowcore` | **Rock** | `0.498` |
| 1843 | The Texas-Jerusalem Crossroads | Lift To Experience | `shoegaze, post-rock, neo-psychedelic` | **Rock** | `0.69` |
| 1844 | Headlights | Alex G | `` | **Other / Unclassified** | `0.0` |
| 1845 | Loss Of Life | MGMT | `indie` | **Pop** | `0.591` |
| 1846 | Halo | Juana Molina | `` | **Other / Unclassified** | `0.0` |
| 1847 | This Old Dog | Mac DeMarco | `indie, lo-fi indie` | **Pop** | `0.622` |
| 1848 | Little Dark Age | MGMT | `indie` | **Pop** | `0.591` |
| 1849 | Nootropics | Lower Dens | `dream pop` | **Pop** | `0.472` |
| 1850 | Performance | Outfit | `` | **Other / Unclassified** | `0.0` |
| 1851 | The Gasoline Age | East River Pipe | `jangle pop` | **Pop** | `0.298` |
| 1852 | 7 | Beach House | `dream pop` | **Pop** | `0.472` |
| 1853 | Scratch It | U.S. Girls | `art pop` | **Pop** | `0.549` |
| 1854 | Adiós Señor Pussycat | Michael Head & The Red Elastic Band | `` | **Other / Unclassified** | `0.0` |
| 1855 | I Had A New York Girlfriend | Robert Forster | `jangle pop` | **Pop** | `0.298` |
| 1856 | San Francisco | American Music Club | `slowcore` | **Other / Unclassified** | `0.29` |
| 1857 | Bury the Key | TOPS | `` | **Other / Unclassified** | `0.0` |
| 1858 | Dirty Projectors | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1859 | nijimusi | OOIOO | `neo-psychedelic, noise rock, shibuya-kei, krautrock, post-rock, experimental, psychedelic rock, avant-garde` | **Rock** | `0.714` |
| 1860 | The Lamb as Effigy | Sprain | `slowcore, noise rock, post-rock, shoegaze` | **Rock** | `0.682` |
| 1861 | Remember Pepper? | Still Corners | `dream pop` | **Pop** | `0.472` |
| 1862 | Swimmer | Tennis | `` | **Other / Unclassified** | `0.0` |
| 1863 | Dusk at Cubist Castle | The Olivia Tremor Control | `neo-psychedelic, psychedelic rock` | **Rock** | `0.561` |
| 1864 | David Live | David Bowie | `glam rock, art rock` | **Rock** | `0.556` |
| 1865 | Tranquility Base Hotel & Casino | Arctic Monkeys | `indie, garage rock` | **Rock** | `0.672` |
| 1866 | Twin Shadow | Twin Shadow | `` | **Other / Unclassified** | `0.0` |
| 1867 | Think Tank | Blur | `britpop, alternative rock` | **Punk / Alternative** | `0.559` |
| 1868 | Role Model Hermit | mary in the junkyard | `` | **Other / Unclassified** | `0.0` |
| 1869 | The Prettiest Curse | Hinds | `` | **Other / Unclassified** | `0.0` |
| 1870 | Bless This Mess | U.S. Girls | `art pop` | **Pop** | `0.549` |
| 1871 | Heartland | Owen Pallett | `` | **Other / Unclassified** | `0.0` |
| 1872 | RELAXER | alt-J | `indie, indie rock` | **Rock** | `0.725` |
| 1873 | Real Life | Joan As Police Woman | `` | **Other / Unclassified** | `0.0` |
| 1874 | Somersault | Beach Fossils | `dream pop, surf rock, shoegaze` | **Rock** | `0.614` |
| 1875 | Jubilee | Japanese Breakfast | `` | **Other / Unclassified** | `0.0` |
| 1876 | Sons Of | Sam Prekop | `post-rock` | **Rock** | `0.494` |
| 1877 | Field Music (Measure) | Field Music | `` | **Other / Unclassified** | `0.0` |
| 1878 | It Goes On | Westside Cowboy | `` | **Other / Unclassified** | `0.0` |
| 1879 | Sparkle Hard | Stephen Malkmus & The Jicks | `` | **Other / Unclassified** | `0.0` |
| 1880 | Charm | Clairo | `bedroom pop` | **Pop** | `0.378` |
| 1881 | Girl with Basket of Fruit | Xiu Xiu | `art pop, noise rock` | **Pop** | `0.636` |
| 1882 | Historian | Lucy Dacus | `` | **Other / Unclassified** | `0.0` |
| 1883 | Nassau | The Sea and Cake | `post-rock` | **Rock** | `0.494` |
| 1884 | Rebound | Eleanor Friedberger | `` | **Other / Unclassified** | `0.0` |
| 1885 | Halcyon Digest | Deerhunter | `neo-psychedelic, dream pop, shoegaze, noise rock` | **Rock** | `0.723` |
| 1886 | Skeleton Tree | Nick Cave & The Bad Seeds | `` | **Other / Unclassified** | `0.0` |
| 1887 | Lamp Lit Prose | Dirty Projectors | `art pop` | **Pop** | `0.549` |
| 1888 | everything is alive | Slowdive | `shoegaze, dream pop, slowcore` | **Rock** | `0.498` |
| 1889 | Salad Days Demos | Mac DeMarco | `indie, lo-fi indie` | **Pop** | `0.622` |
| 1890 | Masterpiece | Big Thief | `` | **Other / Unclassified** | `0.0` |
| 1891 | Bloom | Beach House | `` | **Other / Unclassified** | `0.0` |
| 1892 | Forever Endeavour | Ron Sexsmith | `` | **Other / Unclassified** | `0.0` |
| 1893 | Rare Birds | Jonathan Wilson | `neo-psychedelic` | **Rock** | `0.408` |
| 1894 | Deep Down Happy | Sports Team | `` | **Other / Unclassified** | `0.0` |
| 1895 | McCartney III | Paul McCartney | `` | **Other / Unclassified** | `0.0` |
| 1896 | A Moon Shaped Pool | Radiohead | `art rock, alternative rock` | **Rock** | `0.649` |
| 1897 | Brilliant Sanity | Teleman | `` | **Other / Unclassified** | `0.0` |
| 1898 | Sunlit Youth | Local Natives | `` | **Other / Unclassified** | `0.0` |
| 1899 | The Main Thing | Real Estate | `jangle pop, dream pop, surf rock` | **Rock** | `0.519` |
| 1900 | Live at the Royal Albert Hall | Arctic Monkeys | `indie, garage rock` | **Rock** | `0.672` |
| 1901 | Dedicated to Bobby Jameson | Ariel Pink | `neo-psychedelic` | **Rock** | `0.408` |
| 1902 | Modern Vampires of the City | Vampire Weekend | `` | **Other / Unclassified** | `0.0` |
| 1903 | Port Of Morrow | The Shins | `` | **Other / Unclassified** | `0.0` |
| 1904 | 7s | Avey Tare | `neo-psychedelic` | **Rock** | `0.408` |
| 1905 | Swing Lo Magellan | Dirty Projectors | `` | **Other / Unclassified** | `0.0` |
| 1906 | Melody's Echo Chamber | Melody's Echo Chamber | `neo-psychedelic, dream pop, psychedelic rock` | **Rock** | `0.643` |