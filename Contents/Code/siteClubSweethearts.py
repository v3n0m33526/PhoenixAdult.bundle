import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    searchData.encoded = searchData.title.replace(' ', '_').replace('\'', '')
    sceneURL = PAsearchSites.getSearchSearchURL(siteNum) + searchData.encoded
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    titleNoFormatting = detailsPageElements.xpath('//h3[@class="dvd-title mb-0 mt-0"]/span')[0].text_content().strip()
    curID = PAutils.Encode(sceneURL)
    date = detailsPageElements.xpath('//p[@class="mt-10 letter-space-1"]')[0].text_content().split('DATE ADDED:')[1].split('|', 1)[0].strip()
    releaseDate = parse(date).strftime('%Y-%m-%d')

    if searchData.date:
        score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
    else:
        score = 90

    results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [ClubSeventeen] %s' % (titleNoFormatting, releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAutils.Decode(metadata_id[0])
    if not sceneURL.startswith('http'):
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + sceneURL
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//h3[@class="dvd-title mb-0 mt-0"]/span')[0].text_content().strip()

    # Summary
    metadata.summary = detailsPageElements.xpath('//p[@class="mt-0 hidden-lg"]')[0].text_content().strip()

    # Studio
    metadata.studio = PAsearchSites.getSearchSiteName(siteNum)

    # Tagline and Collection(s)
    metadata.collections.clear()
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    if Prefs['collections_addsitename']:
        metadata.collections.add(tagline)

    series = detailsPageElements.xpath('//p[@class="mt-10 letter-space-1"]/a')
    if series and Prefs['collections_addseries']:
        metadata.collections.add(series[0].text_content().strip())

    # Release Date
    date = detailsPageElements.xpath('//p[@class="mt-10 letter-space-1"]')[0].text_content().split('DATE ADDED:')[1].split('|', 1)[0].strip()
    if date:
        date_object = datetime.strptime(date, '%d-%m-%Y')
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//div[@class="item-tag mt-5"]/a/span'):
        genreName = genreLink.text_content().strip().lower()

        movieGenres.addGenre(genreName)

    # Actors
    movieActors.clearActors()
    for actorLink in detailsPageElements.xpath('//div[@class="middle"]/p/a'):
        actorName = str(actorLink.text_content().strip())
        actorPhotoURL = ''

        actorPageURL = PAsearchSites.getSearchBaseURL(siteNum) + '/' + actorLink.get("href")
        req = PAutils.HTTPRequest(actorPageURL)
        actorPage = HTML.ElementFromString(req.text)
        img = actorPage.xpath('//img[@class="model-profile-image"]/@src')
        if img:
            actorPhotoURL = img[0]
            if 'http' not in actorPhotoURL:
                actorPhotoURL = PAsearchSites.getSearchBaseURL(siteNum) + actorPhotoURL

        movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    art = []
    xpaths = [
        '//div[@class="ratio-16-9 video-item static-item progressive-load"]/@data-image'
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
                if width > 1 or height > width:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                if width > 100 and width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
            except:
                pass

    return metadata
