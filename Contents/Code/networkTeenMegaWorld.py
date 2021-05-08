import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    for searchPageNum in range(1, 3):
        url = PAsearchSites.getSearchSearchURL(siteNum) + '%s&page=%d' % (searchData.encoded, searchPageNum)
        req = PAutils.HTTPRequest(url)
        searchResults = HTML.ElementFromString(req.text)
        for searchResult in searchResults.xpath('//article'):
            if searchResult.xpath('//article'):
                titleNoFormatting = searchResult.xpath('.//h1')[0].text_content().strip()
                titleNoFormatting = PAutils.parseTitle(titleNoFormatting, siteNum)

                curID = PAutils.Encode(searchResult.xpath('.//a/@href')[0])
                releaseDate = parse(searchResult.xpath('.//time')[0].text_content()).strftime('%Y-%m-%d')
                subSite = searchResult.xpath('.//div[@class="site"]/a')[0].text_content().replace('.com', '').strip()

                if searchData.date:
                    score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
                else:
                    score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

                results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [TMW/%s] %s' % (titleNoFormatting, subSite, releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    title = detailsPageElements.xpath('//div[@class="title-line"]/h1')[0].text_content().strip()
    title = PAutils.parseTitle(title, siteNum)
    metadata.title = title

    # Summary
    metadata.summary = detailsPageElements.xpath('//div[@class="text"]//p')[0].text_content().strip()

    # Studio
    metadata.studio = 'Teen Mega World'

    # Tagline and Collection(s)
    metadata.collections.clear()
    tagline = detailsPageElements.xpath('//div[@class="site"]/a')[0].text_content().replace('.com', '').strip()
    metadata.tagline = tagline
    if Prefs['collections_addsitename']:
        metadata.collections.add(tagline)

    # Release Date
    date = detailsPageElements.xpath('//div[@class="date"]//time')[0].text_content().strip()
    date_object = parse(date)
    metadata.originally_available_at = date_object
    metadata.year = metadata.originally_available_at.year

    # Actors
    movieActors.clearActors()
    for actorLink in detailsPageElements.xpath('//div[@class="video"]//div[@class="site"]//a[position() > 1]'):
        actorName = actorLink.text_content().strip()

        actorPageURL = actorLink.get('href')
        req = PAutils.HTTPRequest(actorPageURL)
        actorPageElements = HTML.ElementFromString(req.text)
        actorPhotoURL = PAsearchSites.getSearchBaseURL(siteNum) + actorPageElements.xpath('//div[@class="photo"]//img/@data-src')[0]

        movieActors.addActor(actorName, actorPhotoURL)

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//ul[@class="tag-list"]//a'):
        genreName = genreLink.text_content().strip()

        movieGenres.addGenre(genreName)

    # Posters
    art = []
    xpaths = [
        '//video/@poster',
        '//deo-video/@cover-image',
    ]
    for xpath in xpaths:
        for poster in detailsPageElements.xpath(xpath):
            art.append(poster)

    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                if not posterUrl.startswith('http'):
                    posterUrl = PAsearchSites.getSearchBaseURL(siteNum) + posterUrl
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
