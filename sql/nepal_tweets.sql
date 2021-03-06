SELECT 
	t.id,
	t.tweet_id,
	REPLACE(REPLACE(REPLACE(text, '\r', ' '), '\n', ' '), '\t', ' ') as text,
	created_at,
	t.when_added,
	source,
	source_url,
	entities,
	lang,
	truncated,
	possibly_sensitive,
	coordinates,
	in_reply_to_status_id,
	in_reply_to_screen_name,
	in_reply_to_user_id,
	favorite_count,
	retweet_count,
	is_headline,
	quoted_status_id,
	is_a_retweet,
	retweeted_status_id,
	user_id,
	is_filtered,
	url_expanded
FROM tweet_2017 t join event_tweet_2017 et on t.tweet_id = et.tweet_id
WHERE et.event_id IN (6259, 6260, 6261, 6262, 6263, 6264, 6265, 6266, 6267, 6268, 6269, 6270, 6271, 6272, 6273, 6274, 6275, 6276, 6277, 6278, 6279, 6280, 6281, 6282, 6283, 6284, 6285, 6286, 6287, 6288, 6289, 6290, 6291, 6292, 6293, 6294, 6295, 6296, 6297, 6298, 6299, 6300, 6301, 6302, 6303, 6304, 6305, 6306, 6307, 6308, 6309, 6310, 6311, 6312, 6313, 6314, 6315, 6316);
