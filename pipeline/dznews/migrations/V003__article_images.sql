-- The lead image each outlet publishes with an article (media:content, an enclosure or
-- the first <img> of the feed item). Stored as a link only: the image stays on the
-- publisher's server, nothing is downloaded or re-hosted.
ALTER TABLE raw.articles ADD COLUMN IF NOT EXISTS image_url text;
