/** Editorial programme order approved by the user; never a model-strength rank.
 * API-Football competition IDs distinguish identically named leagues/countries.
 * Unlisted IDs follow these groups, ordered by country, name, then ID in D1.
 */
export const PROGRAM_COMPETITION_GROUPS = [
  {key:'major_european_leagues',ids:[39,140,135,78,61]}, // England, Spain, Italy, Germany, France
  {key:'uefa_club_cups',ids:[2,3,848]}, // Champions, Europa, Conference
  {key:'championship',ids:[40]},
  {key:'major_domestic_cups',ids:[45,48,143,81,137,66]}, // FA, League Cup, Copa, DFB, Coppa, Coupe
  {key:'other_european_top_divisions',ids:[88,94,203,144,179]},
  {key:'asian_and_american_top_divisions',ids:[296,98,292,71,128,253,307]},
  {key:'lower_divisions',ids:[141,136,79,62,41,42,43]}
] as const;

export const PROGRAM_COMPETITION_ORDER=PROGRAM_COMPETITION_GROUPS.flatMap(group=>[...group.ids]);
