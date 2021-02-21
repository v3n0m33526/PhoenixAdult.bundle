import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    sceneID = searchData.title.split(' ', 1)[0]
    if unicode(sceneID, 'UTF-8').isdigit():
        searchData.title = searchData.title.replace(sceneID, '', 1).strip()
    else:
        sceneID = None

    if sceneID:
        url = PAsearchSites.getSearchBaseURL(siteNum) + '/videos/1/' + sceneID
        req = PAutils.HTTPRequest(url)
        detailsPageElements = HTML.ElementFromString(req.text)

        curID = PAutils.Encode(url)
        titleNoFormatting = detailsPageElements.xpath('//h1')[0].text_content().strip()

        results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name=titleNoFormatting, score=100, lang=lang))
    else:
        searchData.encoded = searchData.title.replace(' ', '+')
        req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded)
        searchResults = HTML.ElementFromString(req.text)
        for searchResult in searchResults.xpath('//div[@id="content"]//div[contains(@class, "card-body")]'):
            titleNoFormatting = searchResult.xpath('.//a/@title')[0]
            url = searchResult.xpath('.//a/@href')[0]

            date = searchResult.xpath('.//small[@class="text-muted"]/@datetime')
            releaseDate = parse(date[0]).strftime('%Y-%m-%d') if date else ''

            sceneCoverURL = searchResult.xpath('.//..//img/@data-src')[0]
            if not sceneCoverURL.startswith('http'):
                sceneCoverURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneCoverURL
            sceneCover = PAutils.Encode(sceneCoverURL)
            curID = PAutils.Encode(url)

            if searchData.date and releaseDate:
                score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
            else:
                score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, sceneCover), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    if 'http' not in sceneURL:
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    scenePoster = PAutils.Decode(metadata_id[2]) if len(metadata_id) > 2 else None
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//h1')[0].text_content().strip()

    # Summary
    metadata.summary = detailsPageElements.xpath('//div[@id="descriptionBoxMobile"]')[0].text_content().strip()

    # Studio
    metadata.studio = 'DDFProd'

    # Tagline / Collection
    metadata.collections.clear()
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    if Prefs['collections_addsitename']:
        metadata.collections.add(tagline)

    # Release Date
    date_object = None
    for item in detailsPageElements.xpath('//div[@id="video-specs"]//div//p'):
        try:
            item = item.text_content().strip()
            if item:
                date_object = parse(item)
                break
        except:
            pass

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//ul[contains(@class, "tags")]//li'):
        genreName = genreLink.text_content().strip()

        movieGenres.addGenre(genreName)

    if date_object:
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Actors
    movieActors.clearActors()
    for actorLink in detailsPageElements.xpath('//div[contains(@class, "pornstar-card")]//img'):
        actorName = actorLink.xpath('.//../@title')[0]
        actorPhotoURL = 'http:' + actorLink.get('data-src')

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    art = []
    if scenePoster:
        art.append(scenePoster)

    xpaths = [
        '//meta[@itemprop="thumbnailUrl"]/@content',
        '//div[@id="innerVideoBlock"]//img/@src',
        '//div[@id="photoSliderGuest"]//a/@href'
    ]
    for xpath in xpaths:
        for img in detailsPageElements.xpath(xpath):
            art.append(img)

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
                if (width > 1 or height > width) and width < height:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100 and width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
