import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    if not searchData.filename:
        return results

    url = PAsearchSites.getSearchSearchURL(siteNum) + '/scenes?parse=' + urllib.quote(searchData.filename)
    req = PAutils.HTTPRequest(url)
    searchResults = req.json()
    if searchResults and 'data' in searchResults and searchResults['data']:
        for searchResult in searchResults['data']:
            curID = searchResult['_id']
            titleNoFormatting = searchResult['title']
            siteName = searchResult['site']['name']

            date = searchResult['date']
            releaseDate = parse(date).strftime('%Y-%m-%d')

            if searchData.date and releaseDate:
                score = 100 - Util.LevenshteinDistance(searchData.dateFormat(), releaseDate)
            else:
                score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [MetadataAPI/%s] %s' % (titleNoFormatting, siteName, releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    metadata_id = str(metadata.id).split('|')
    sceneID = metadata_id[0]

    url = PAsearchSites.getSearchSearchURL(siteNum) + '/scenes/' + sceneID
    req = PAutils.HTTPRequest(url)
    detailsPageElements = req.json()['data']

    # Title
    metadata.title = detailsPageElements['title']

    # Summary
    metadata.summary = detailsPageElements['description']

    # Studio
    metadata.studio = detailsPageElements['site']['name']

    # Tagline and Collection(s)
    metadata.collections.clear()
    tagline = detailsPageElements['site']['name']
    metadata.tagline = tagline
    metadata.collections.add(tagline)

    # Release Date
    date = detailsPageElements['date']
    if date:
        date_object = parse(date)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements['tags']:
        genreName = genreLink['name']

        movieGenres.addGenre(genreName)

    # Actors
    movieActors.clearActors()
    for actorLink in detailsPageElements['performers']:
        actorName = actorLink['name']
        actorPhotoURL = actorLink['image']

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    art = [
        detailsPageElements['posters']['large'],
        detailsPageElements['background']['large'],
    ]

    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100 and width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
