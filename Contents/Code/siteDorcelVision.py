import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded)
    searchResults = HTML.ElementFromString(req.text)
    for searchResult in searchResults.xpath('//a[contains(@class, "movies")]'):
        titleNoFormatting = searchResult.xpath('.//img/@alt')[0].strip()
        curID = PAutils.Encode(searchResult.get('href'))

        score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [%s]' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum)), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Summary
    try:
        paragraph = detailsPageElements.xpath('//meta[@name="twitter:description"]/@content')[0].strip()
    except:
        try:
            paragraph = detailsPageElements.xpath('//div[@id="summaryList"]')[0].text_content().strip()
        except:
            paragraph = ''
    metadata.summary = paragraph.replace('</br>', '\n').replace('<br>', '\n').strip()

    # Tagline
    metadata.collections.clear()
    tagline = 'Dorcel Vision'
    try:
        taglineFirst = detailsPageElements.xpath('//div[@class="col-xs-12 col-md-6 with-margin"]//div[@class="entries"]/div')
        tagline = taglineFirst[0].xpath('//a')[0].text_content().strip()
        if Prefs['collections_addsitename']:
            metadata.collections.add('Dorcel Vision')
            metadata.collections.add(tagline)
    except:
        pass
    metadata.tagline = tagline
    metadata.studio = tagline
    

    # Title
    metadata.title = detailsPageElements.xpath('//h1')[0].text_content().strip()

    # Genres
    movieGenres.clearGenres()

    # Release Date
    try:
        date_object = parse(detailsPageElements.xpath('//div[@class="col-xs-12 col-md-6 with-margin"]/div[@class="entries"]/div[@class="entries"]')[0].text_content().strip().replace("Production year:", ""))

        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year
    except:
        date = ''

    # Actors
    movieActors.clearActors()
    for actorLink in detailsPageElements.xpath('//div[contains(@class, "casting")]//div[contains(@class, "slider-xl")]//div[@class="col-xs-2"]'):
        actorName = actorLink.xpath('.//a/strong')[0].text_content().strip()
        actorPhotoURL = actorLink.xpath('.//img/@data-src')[0]
        if not actorPhotoURL.startswith('http:'):
            actorPhotoURL = PAsearchSites.getSearchBaseURL(siteNum) + actorPhotoURL

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    art = []
    try:
        poster = detailsPageElements.xpath('//div[contains(@class, "covers")]/a[contains(@class, "cover")]/@href')[0].strip()
        coverURL = (PAsearchSites.getSearchBaseURL(siteNum) + poster).replace('https:', 'http:')
        art.append(coverURL)
    except:
        pass

    try:
        photoBoxA = detailsPageElements.xpath('//div[@class="slider-part screenshots"]')[0]
        photoBoxB = photoBoxA.xpath('//div[contains(@class, "slider-xl")]/div[@class="slides"]/div[@class="col-xs-2"]/a/@href')

        for photo in photoBoxB:
            photoURL = (PAsearchSites.getSearchBaseURL(siteNum) + photo.strip()).replace('https:', 'http:').replace('blur9/', '/')
            art.append(photoURL)
    except:
        pass

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
