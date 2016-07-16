import pstats
p = pstats.Stats('profile_results')
p.sort_stats('cumulative').print_stats(20)