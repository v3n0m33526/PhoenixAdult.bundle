import PAsearchSites
import PAutils


def search(results, lang, siteNum, searchData):
    if searchData.date:
        url = PAsearchSites.getSearchSearchURL(siteNum) + 'date/' + searchData.date + '/' + searchData.date
        req = PAutils.HTTPRequest(url)
        searchResults = HTML.ElementFromString(req.text)
        for searchResult in searchResults.xpath('//div[contains(@class, "content-grid-item")]'):
            titleNoFormatting = searchResult.xpath('.//span[@class="title"]/a')[0].text_content().strip()
            curID = searchResult.xpath('.//span[@class="title"]/a/@href')[0].split('/')[3]
            releaseDate = parse(searchResult.xpath('.//span[@class="date"]')[0].text_content().strip()).strftime('%Y-%m-%d')

            if searchData.date:
                score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
            else:
                score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

            results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    sceneID = searchData.title.split()[0]
    if unicode(sceneID, 'utf-8').isdigit():
        sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + '/video/watch/' + sceneID
        req = PAutils.HTTPRequest(sceneURL)
        detailsPageElements = HTML.ElementFromString(req.text)

        detailsPageElements = detailsPageElements.xpath('//div[contains(@class, "content-pane-title")]')[0]
        titleNoFormatting = detailsPageElements.xpath('//h2')[0].text_content()
        curID = sceneID
        releaseDate = parse(detailsPageElements.xpath('//span[@class="date"]')[0].text_content().strip()).strftime('%Y-%m-%d')

        score = 100

        results.Append(MetadataSearchResult(id='%s|%d' % (curID, siteNum), name='%s [%s] %s' % (titleNoFormatting, PAsearchSites.getSearchSiteName(siteNum), releaseDate), score=score, lang=lang))

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors):
    metadata_id = str(metadata.id).split('|')
    sceneURL = PAsearchSites.getSearchBaseURL(siteNum) + '/video/watch/' + metadata_id[0]
    req = PAutils.HTTPRequest(sceneURL)
    detailsPageElements = HTML.ElementFromString(req.text)

    # Title
    metadata.title = detailsPageElements.xpath('//div[contains(@class, "content-pane-title")]//h2')[0].text_content().strip()

    # Summary
    description = detailsPageElements.xpath('//div[@class="col-12 content-pane-column"]/div')
    if not description:
        description = ''
        for paragraph in detailsPageElements.xpath('//div[@class="col-12 content-pane-column"]//p'):
            description += '\n\n' + paragraph.text_content()
    else:
        description = description[0].text_content()

    metadata.summary = description.strip()

    # Studio
    metadata.studio = 'Nubiles'

    # Collections / Tagline
    metadata.collections.clear()
    tagline = PAsearchSites.getSearchSiteName(siteNum)
    metadata.tagline = tagline
    if Prefs['collections_addsitename']:
        metadata.collections.add(tagline)

    # Release Date
    date = detailsPageElements.xpath('//div[contains(@class, "content-pane")]//span[@class="date"]')[0].text_content().strip()
    if date:
        date_object = parse(date)
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    movieGenres.clearGenres()
    for genreLink in detailsPageElements.xpath('//div[@class="categories"]/a'):
        genreName = genreLink.text_content().strip()

        movieGenres.addGenre(genreName)

    # Actors
    movieActors.clearActors()
    for actorLink in detailsPageElements.xpath('//div[contains(@class, "content-pane-performer")]/a'):
        actorName = actorLink.text_content().strip()
        actorPageURL = PAsearchSites.getSearchBaseURL(siteNum) + actorLink.get('href')
        req = PAutils.HTTPRequest(actorPageURL)
        actorPage = HTML.ElementFromString(req.text)
        actorSpecs = actorPage.xpath('//div[contains(@class, "model-profile-desc")]/h5/text()')
        actorBio = actorPage.xpath('//p[@class="model-bio"]')[0].text_content().strip()
        if actorBio:
            actorGender = ''
            for spec in actorSpecs:
                if 'Figure' in spec:
                    actorGender = 'female'
            if (actorGender == ''):
                if ('she' in actorBio) or ('her' in actorBio):
                    actorGender = 'female'            

                if (' he' in actorBio) or ('him' in actorBio) or ('his' in actorBio):
                    actorGender = 'male'
        
            if actorGender == 'female':
                actorPhotoURL = 'http:' + actorPage.xpath('//div[contains(@class, "model-profile")]//img/@src')[0]
                movieActors.addActor(actorName, actorPhotoURL)

    # Posters
    art = []
    xpaths = [
        '//div[@class="content-grid-item col-6 col-sm-4 col-lg-3" and .//a[text()="' + metadata.title + '"]]//picture/img/@*[contains(name(), "srcset")]',
        '//div[@class="content-grid-item col-6 col-sm-4 col-md-3 col-lg-2-point-4 col-xl-2" and .//a[text()="' + metadata.title + '"]]//picture/img/@*[contains(name(), "srcset")]',
        '//video/@poster',        
    ]
    for xpath in xpaths:
        for poster in detailsPageElements.xpath(xpath):
            if (',' in poster):
                poster = poster.split(' ')[-2].split(',')[1]
            if not poster.startswith('http'):
                poster = 'http:' + poster
            art.append(poster)

    galleryURL = 'https://nubiles-porn.com/photo/gallery/' + metadata_id[0]
    req = PAutils.HTTPRequest(galleryURL)
    photoPageElements = HTML.ElementFromString(req.text)
    for poster in photoPageElements.xpath('//div[@class="img-wrapper"]//source[1]/@src'):
        if not poster.startswith('http'):
            poster = 'http:' + poster

        art.append(poster)
        
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
