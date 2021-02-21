import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    searchResultsURLs = []
    googleResults = PAutils.getFromGoogleSearch(searchData.title, siteNum)

    for sceneURL in googleResults:
        if sceneURL not in searchResultsURLs:
            url = None
            if '/scene/' in sceneURL:
                url = sceneURL
            else:
                for item in ['/trailers/', '/updates/']:
                    if item in sceneURL:
                        url = sceneURL.replace(item, '/1/scene/').replace('.html', '/')
                        break

            if url and url not in searchResultsURLs:
                searchResultsURLs.append(url)

    for url in searchResultsURLs:
        req = PAutils.HTTPRequest(url)
        detailsPageElements = HTML.ElementFromString(req.text)
        curID = PAutils.Encode(url)
        titleNoFormatting = detailsPageElements.xpath('//h4')[0].text_content().strip()
        releaseDate = searchData.dateFormat() if searchData.date else ''

        score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, releaseDate), name='%s [FPN/%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    searchData.encoded = searchData.title.replace(' ', '_')
    req = PAutils.HTTPRequest(PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded)
    searchResults = HTML.ElementFromString(req.text)
    for searchResult in searchResults.xpath('//div[contains(@class, "section-updates")]/div[contains(@class, "scene-update")]'):
        curID = PAutils.Encode(searchResult.xpath('.//a/@href')[0])
        titleNoFormatting = searchResult.xpath('.//div[contains(@class, "scene-info")]//a')[0].text_content().strip()
        poster = PAutils.Encode(searchResult.xpath('.//img/@src')[0])
        releaseDate = searchData.dateFormat() if searchData.date else ''

        score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%s|%d|%s|%s' % (curID, siteNum, releaseDate, poster), name='%s [FPN/%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    sceneDate = metadata_id[2]
    scenePoster = PAutils.Decode(metadata_id[3]) if len(metadata_id) > 3 else None
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//h4')[0].text_content().strip()

    # Summary
    metadata.summary = detailsPageElements.xpath('//p[@class="hide-for-small-only"]')[0].text_content().strip()

    # Studio
    metadata.studio = 'Full Porn Network'

    # Tagline and Collection(s)
    metadata.collections.clear()
    for seriesName in [metadata.studio, PAsearchSites.getSearchSiteName(siteNum)]:
        if Prefs['collections_addsitename']:
            metadata.collections.add(seriesName)

    # Release Date
    if sceneDate:
        date_object = parse(sceneDate)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//div[@class="small-12"]//a[contains(@href, "/category/")]/text()'):
        genreName = genreLink.strip()

        movieGenres.addGenre(genreName)

    # Actors
    movieActors.clearActors()
    for actorLink in detailsPageElements.xpath('//div[@class="small-12"]//a[contains(@href, "/model/")]/@href'):
        req = PAutils.HTTPRequest(PAsearchSites.getSearchBaseURL(siteNum) + actorLink)
        actorPage = HTML.ElementFromString(req.text)
        actorName = actorPage.xpath('//h1')[0].text_content().strip()
        actorPhotoURL = actorPage.xpath('//img[@alt="%s"]/@src' % actorName)[0]

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    art = []
    if scenePoster:
        art.append(scenePoster)

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
