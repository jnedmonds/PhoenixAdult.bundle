import PAsearchSites
import PAutils


def getNaughtyAmerica(sceneID):
    re_image = re.compile(r'images\d+', re.IGNORECASE)

    req = PAutils.HTTPRequest('https://www.naughtyamerica.com/scene/0' + sceneID)
    scenePageElements = HTML.ElementFromString(req.text)

    photoElements = scenePageElements.xpath('//div[contains(@class, "contain-scene-images") and contains(@class, "desktop-only")]/a/@href')

    photos = []
    for photo in photoElements:
        img = 'https:' + re_image.sub('images1', photo, 1)
        photos.append(img)

    results = {
        'id': int(sceneID),
        'title': scenePageElements.xpath('//div[contains(@class, "scene-info")]//h1/text()')[0],
        'site': scenePageElements.xpath('//a[@class="site-title grey-text link"]/text()')[0],
        'published_at': parse(scenePageElements.xpath('//div[contains(@class, "date-tags")]//span/text()')[0]),
        'fantasies': scenePageElements.xpath('//div[contains(@class, "categories") and contains(@class, "grey-text")]/a/text()'),
        'performers': scenePageElements.xpath('//div[contains(@class, "performer-list")]/a/text()'),
        'synopsis': scenePageElements.xpath('//div[contains(@class, "synopsis") and contains(@class, "grey-text")]//h2')[0].tail.strip(),
        'photos': photos,
    }

    return results


def search(results, lang, siteNum, searchData):
    Log('---- siteNaughtyAmerica-search(): starting with title: %s' % searchData.title)

    sceneID = searchData.title.split(' ', 1)[0]
    if unicode(sceneID, 'UTF-8').isdigit():
        searchData.title = searchData.title.replace(sceneID, '', 1).strip()
    else:
        sceneID = None

    Log('---- siteNaughtyAmerica-search(): seaching')

    searchURL = '%s%s&_gl=1' % (PAsearchSites.getSearchSearchURL(siteNum), slugify(searchData.title, separator='+'))
    if sceneID:
        scenePageElements = getNaughtyAmerica(sceneID)
        titleNoFormatting = PAutils.parseTitle(scenePageElements['title'], siteNum)
        if Prefs['debug_enable']:
            Log('---- siteNaughtyAmerica-search(): found result title:     %s' % titleNoFormatting)

        curID = scenePageElements['id']
        releaseDate = scenePageElements['published_at'].strftime('%Y-%m-%d')
        siteName = scenePageElements['site']

        if sceneID:
            score = 100 - Util.LevenshteinDistance(sceneID, curID)
        elif searchData.date:
            score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
        else:
            score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

        results.Append(MetadataSearchResult(id='%d|%d' % (curID, siteNum), name='%s [%s] %s' % (titleNoFormatting, siteName, releaseDate), score=score, lang=lang))
    else:
        req = PAutils.HTTPRequest(searchURL)
        searchResults = HTML.ElementFromString(req.text)

        try:
            lastPage = searchResults.xpath('//li/a[./i[contains(@class, "double")]]/@href')[0]

            match = re.search(r'\d+(?=#)', lastPage)
            if match:
                pagination = int(match.group(0)) + 2
        except:
            pagination = 3

        if 'pornstar' in req.url:
            searchxPath = '//div[contains(@class, "scene-item")]'
        else:
            searchxPath = '//div[@class="scene-grid-item"]'

        for idx in range(2, pagination):
            for searchResult in searchResults.xpath(searchxPath):
                #titleNoFormatting = PAutils.parseTitle(searchResult.xpath('./a//@title')[0].strip(), siteNum)
                curID = int(searchResult.xpath('./a/@data-scene-id')[0])
                
                # Get the title from the href
                tempTitle = searchResult.xpath('./a//@href')[0].strip()
                newTitle = tempTitle.replace('https://www.naughtyamerica.com/scene/','')
                newTitle = newTitle.replace(str(curID),'')
                newTitle = newTitle[:-1]
                titleNoFormatting = PAutils.parseTitle(newTitle, siteNum)
                if Prefs['debug_enable']:
                    Log('---- siteNaughtyAmerica-search(): found result title:     %s' % titleNoFormatting)
                
                releaseDate = parse(searchResult.xpath('./p[@class="entry-date"]/text()')[0]).strftime('%Y-%m-%d')
                siteName = searchResult.xpath('.//a[@class="site-title"]')[0].text_content()

                if searchData.date:
                    score = 100 - Util.LevenshteinDistance(searchData.date, releaseDate)
                else:
                    score = 100 - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

                results.Append(MetadataSearchResult(id='%d|%d' % (curID, siteNum), name='%s [%s] %s' % (titleNoFormatting, siteName, releaseDate), score=score, lang=lang))
                if Prefs['debug_enable']:
                    Log('---- siteNaughtyAmerica-search(): sceneID:                %s' % curID)
                    Log('---- siteNaughtyAmerica-search(): percentage match:       %s' % score)

                # break out of loop if the score is higher than 80%                
                if score > 80:
                    foundTitle = True
                    break

            if pagination > 1 and not pagination == idx + 1:
                if 'pornstar' in req.url:
                    searchURL = '%s/pornstar/%s?related_page=%d' % (PAsearchSites.getSearchBaseURL(siteNum), slugify(searchData.title), idx)
                else:
                    searchURL = '%s%s&page=%d' % (PAsearchSites.getSearchSearchURL(siteNum), slugify(searchData.title, separator='+'), idx)

                req = PAutils.HTTPRequest(searchURL)
                searchResults = HTML.ElementFromString(req.text)

            if foundTitle:
                Log('---- siteNaughtyAmerica-search(): Title found > 80%')
                break

    Log('---- siteNaughtyAmerica-search(): leaving')

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    Log('---- siteNaughtyAmerica-update(): starting')

    metadata_id = str(metadata.id).split('|')
    sceneID = metadata_id[0]
    Log('---- siteNaughtyAmerica-update(): url:               %s' % sceneID)

    detailsPageElements = getNaughtyAmerica(sceneID)

    # Title
    metadata.title = PAutils.parseTitle(detailsPageElements['title'], siteNum)
    if Prefs['debug_enable']:
        Log('---- siteNaughtyAmerica-update(): updating title:    %s' % metadata.title)

    # Summary
    metadata.summary = detailsPageElements['synopsis']

    # Studio
    metadata.studio = 'Naughty America'
    if Prefs['debug_enable']:
        Log('---- siteNaughtyAmerica-update(): updating title:    %s' % metadata.studio)

    # Tagline and Collection(s)
    tagline = detailsPageElements['site']
    metadata.tagline = tagline
    metadata.collections.add(tagline)
    if Prefs['debug_enable']:
        Log('---- siteNaughtyAmerica-update(): adding collection: %s' % tagline)

    # Release Date
    date_object = detailsPageElements['published_at']
    if isinstance(date_object, int):
        date_object = datetime.fromtimestamp(date_object)

    if date_object:
        metadata.originally_available_at = date_object
        metadata.year = metadata.originally_available_at.year

    # Genres
    for genreLink in detailsPageElements['fantasies']:
        genreName = genreLink

        movieGenres.addGenre(genreName)
        if Prefs['debug_enable']:
            Log('---- siteNaughtyAmerica-update(): genres:            %s' % genreName)

    # Actor(s)
    for actorLink in detailsPageElements['performers']:
        actorName = actorLink
        actorPhotoURL = ''

        actorsPageURL = 'https://www.naughtyamerica.com/pornstar/%s' % actorName.lower().replace(' ', '-').replace("'", '')
        req = PAutils.HTTPRequest(actorsPageURL)
        actorsPageElements = HTML.ElementFromString(req.text)
        img = actorsPageElements.xpath('//img[contains(@class, "performer-pic")]/@data-src')
        if img:
            actorPhotoURL = 'https:' + img[0]

        movieActors.addActor(actorName, actorPhotoURL)
        if Prefs['debug_enable']:
            Log('---- siteNaughtyAmerica-update(): actor name:        %s' % actorName)        
            Log('----                            : actor picture:     %s' % actorPhotoURL)

    # Posters
    for img in detailsPageElements['photos']:
        art.append(img)

    images = []
    posterExists = False
    Log('Artwork found: %d' % len(art))
    for idx, posterUrl in enumerate(art, 1):
        if not PAsearchSites.posterAlreadyExists(posterUrl, metadata):
            # Download image file for analysis
            try:
                image = PAutils.HTTPRequest(posterUrl)
                im = StringIO(image.content)
                images.append(image)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if height > width:
                    # Item is a poster
                    metadata.posters[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                    if Prefs['debug_enable']:
                        Log('---- siteNaughtyAmerica-update(): poster:            %s' % posterUrl)
                    posterExists = True
                if width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                    if Prefs['debug_enable']:
                        Log('---- siteNaughtyAmerica-update(): art item:          %s' % posterUrl)
            except:
                pass

    if not posterExists:
        for idx, image in enumerate(images, 1):
            try:
                im = StringIO(image.content)
                images.append(image)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if height > width:
                    # Item is a poster
                    metadata.posters[art[idx - 1]] = Proxy.Media(image.content, sort_order=idx)
                    if Prefs['debug_enable']:
                        Log('---- siteNaughtyAmerica-update(): poster:            %s' % posterUrl)
            except:
                pass

    if not posterExists:
        for idx, image in enumerate(images, 1):
            try:
                im = StringIO(image.content)
                resized_image = Image.open(im)
                width, height = resized_image.size
                # Add the image proxy items to the collection
                if width > 1:
                    # Item is a poster
                    metadata.posters[art[idx - 1]] = Proxy.Media(image.content, sort_order=idx)
                    if Prefs['debug_enable']:
                        Log('---- siteNaughtyAmerica-update(): poster:            %s' % posterUrl)
            except:
                pass

    Log('---- siteNaughtyAmerica-update(): leaving')

    return metadata
