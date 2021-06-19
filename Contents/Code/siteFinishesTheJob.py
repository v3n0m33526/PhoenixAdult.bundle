import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    cookies = {'splash': 'true'}
    req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded, cookies=cookies)
    searchResults = HTML.ElementFromString(req.text)
    
    for searchResult in searchResults.xpath('//div[@class="card scene"]'):
        titleNoFormatting = searchResult.xpath('.//h3[@itemprop="name"]')[0].text_content()
        curID = PAutils.Encode(searchResult.xpath('.//a[contains(@class, "btn-primary")]/@href')[0])
        releaseDate = searchData.dateFormat() if searchData.date else ''

        subSite = curID.replace("https://www.finishesthejob.com/scene/","").split("/")[0]
        if subSite.lower().replace('.com', '').replace(' ', '') == PAsearchSites.getSearchSiteName(siteNum).lower().replace(' ', ''):
            siteScore = 10
        else:
            siteScore = 0

        score = siteScore + 90 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s]' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum)), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    cookies = {'splash': 'true'}
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    sceneDate = metadata_id[2]
    req = PAutils.HTTPRequest(sceneURL, cookies=cookies)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//h1[@itemprop="name"]')[0].text_content().strip()

    # Summary
    metadata.summary = detailsPageElements.xpath('//div[@class="container"]//p[@itemprop="description"]')[0].text_content().strip()

    # Studio
    metadata.studio = 'Finishes The Job'

    # Tagline and Collection(s)
    metadata.collections.clear()
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    if Prefs['collections_addsitename']:
        metadata.collections.add(tagline)

    # Release Date
    if sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Actors
    movieActors.clearActors()
    actors = detailsPageElements.xpath('//div[@class="container"]//h3//a')
    for actorLink in actors:
        actorName = actorLink.text_content()
        actorPhotoURL = ''
        movieActors.addActor(actorName, actorPhotoURL)

    # Genres
    movieGenres.clearGenres()
    genres = detailsPageElements.xpath('//div[@class="container"]//p[1]//a')
    for genreLink in genres:
        genreName = genreLink.text_content().strip()

        movieGenres.addGenre(genreName)

    # Poster
    art = []
    xpaths = [
        '//video/@poster'
    ]

    for xpath in xpaths:
        for img in detailsPageElements.xpath(xpath):
            if not img.startswith('http'):
                img = PAsearchSites.getSearchBaseURL(siteNum) + img
            art.append(img)

    for posterCur in detailsPageElements.xpath('//div[contains(@class, "first-set")]//img'):
        sceneName = posterCur.get('alt')
        if sceneName.lower() == metadata.title.lower():
            art.append(posterCur.get('src'))

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
                if width > 100:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
