import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    query = urllib.quote_plus(searchData.title)
    if searchData.title.lower().startswith("code"):
        directURL = PAsearchSites.getSearchBaseURL(siteNum) + "/site/set-video/code/" + searchData.title.split()[1]
        req = PAutils.HTTPRequest(directURL)
        results.Append(MetadataSearchResult(id='%s|%d|%s' % (PAutils.Encode(directURL), siteNum, "01-01-01"), name='%s [%s] %s' % (searchData.title, PAsearchSites.getSearchSiteName(siteNum), "01-01-01"), score=100, lang=lang))
    else:
        req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + query)
    searchResults = HTML.ElementFromString(req.text)
    for searchResult in searchResults.xpath('//div[contains(@class, "set set-photo")]'):
        titleNoFormatting = searchResult.xpath('.//div[contains(@class, "title")]//a')[0].text_content().title().strip()
        curID = PAutils.Encode(searchResult.xpath('.//a/@href')[0])
        releaseDate = parse(searchResult.xpath('.//div[contains(@class, "release_date")]')[0].text_content().strip()).strftime('%Y-%m-%d')

        if searchData.date:
            score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
        else:
            score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    metadata_id = metadata.id.split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    sceneDate = metadata_id[2]
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//h1[@class="title"]')[0].text_content().title().strip()

    # Summary
    metadata.summary = detailsPageElements.xpath('//p[@class="text"]')[0].text_content()
    

    # Studio
    metadata.studio = PAsearchSites.getSearchSiteName(siteNum)

    # Tagline and Collection(s)
    metadata.collections.clear()
    metadata.tagline = metadata.studio
    metadata.collections.clear()
    if Prefs['collections_addsitename']:
        metadata.collections.add(metadata.studio)

    # Release Date
    if sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.addGenre('Glamcore')
    movieGenres.addGenre('Artistic')

    # Actors
    movieActors.clearActors()
    actors = detailsPageElements.xpath('//h2[@class="starring-models"]/a')
    if actors:
        if len(actors) == 3:
            movieGenres.addGenre('Threesome')
        if len(actors) == 4:
            movieGenres.addGenre('Foursome')
        if len(actors) > 4:
            movieGenres.addGenre('Orgy')

        for actorLink in actors:
            actorName = actorLink.text_content().strip()
            if actorName == "Katy Rose":
                hubName = "Katy R"
            else:
                hubName = actorName
            actorPhotoURL = ''
            actorSearchURL = 'https://www.joymiihub.com/?s=' + hubName.replace(' ', '+').replace('.','')
            req = PAutils.HTTPRequest(actorSearchURL)
            actorSearchPage = HTML.ElementFromString(req.text)
            
            JoymiiHubActors = actorSearchPage.xpath('//ul[@class="gallery-a b d"]//a')
            for hubActorLink in JoymiiHubActors:
                hubActor = hubActorLink.xpath('.//span[not(@class)]/text()')
                if hubActor[0].replace('.','').lower() == hubName.replace('.','').lower():
                    movieActors.addActor(actorName, actorPhotoURL)

    # Posters/Background
    art = []
    xpaths = [
        '//div[@id="video-set-details"]//video[@id="video-playback"]/@poster',
        '(//img[@class="poster"] | //img[@class="cover"])/@src'
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
                if width > 1:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
