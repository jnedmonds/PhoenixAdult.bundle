import PAsearchSites
import PAutils


def get_Token(siteNum):
    url = PAsearchSites.getSearchBaseURL(siteNum)
    token_key = urlparse.urlparse(url).hostname

    token = None
    if token_key and token_key in Dict:
        data = Dict[token_key].split('.')[1] + '=='
        #data = base64.b64decode(data).decode('UTF-8')
        #if json.loads(data)['exp'] > time.time():
        token = Dict[token_key]

    if not token:
        req = PAutils.HTTPRequest(url, 'HEAD')
        if 'instance_token' in req.cookies:
            token = req.cookies['instance_token']

    if token_key and token:
        if token_key not in Dict or Dict[token_key] != token:
            Dict[token_key] = token
            Dict.Save()

    return token


def search(results, lang, siteNum, searchData):
    Log('---- network1service-search(): starting with title: %s' % searchData.title)

    token = get_Token(siteNum)
    headers = {
        'Instance': token,
    }

    sceneID = None
    parts = searchData.title.split()
    if unicode(parts[0], 'UTF-8').isdigit():
        sceneID = parts[0]
        searchData.title = searchData.title.replace(sceneID, '', 1).strip()

    Log('---- network1service-search(): seaching')

    for sceneType in ['scene', 'movie', 'serie', 'trailer']:
        if sceneID and not searchData.title:
            url = PAsearchSites.getSearchSearchURL(siteNum) + '/v2/releases?type=%s&id=%s' % (sceneType, sceneID)
        else:
            url = PAsearchSites.getSearchSearchURL(siteNum) + '/v2/releases?type=%s&search=%s' % (sceneType, searchData.encoded)

        req = PAutils.HTTPRequest(url, headers=headers)
        if req:
            searchResults = req.json()['result']
            for searchResult in searchResults:
                titleNoFormatting = PAutils.parseTitle(searchResult['title'].replace('ï¿½', '\''), siteNum)

                Log('---- network1service-search(): found result title:     %s' % titleNoFormatting)

                releaseDate = parse(searchResult['dateReleased']).strftime('%Y-%m-%d')
                curID = searchResult['id']
                siteName = searchResult['brand'].title()
                subSite = ''
                if 'collections' in searchResult and searchResult['collections']:
                    subSite = searchResult['collections'][0]['name'].strip()
                siteDisplay = '%s/%s' % (siteName, subSite) if subSite else siteName

                score = 100
                if sceneID:
                    score = score - Util.LevenshteinDistance(sceneID, curID)
                else:
                    if searchData.date:
                        score = score - 2 * Util.LevenshteinDistance(searchData.date, releaseDate)
                    score = score - Util.LevenshteinDistance(searchData.title.lower(), titleNoFormatting.lower())

                if sceneType == 'trailer':
                    titleNoFormatting = '[%s] %s' % (sceneType.capitalize(), titleNoFormatting)
                    score = score - 10

                if subSite and PAsearchSites.getSearchSiteName(siteNum).replace(' ', '').lower() != subSite.replace(' ', '').lower():
                    score = score - 10

                results.Append(MetadataSearchResult(id='%s|%d|%s' % (curID, siteNum, sceneType), name='%s [%s] %s' % (titleNoFormatting, siteDisplay, releaseDate), score=score, lang=lang))

        Log('---- network1service-search(): leaving')

    return results


def update(metadata, lang, siteNum, movieGenres, movieActors, art):
    Log('---- network1service-update(): starting')

    metadata_id = str(metadata.id).split('|')
    sceneID = metadata_id[0]
    sceneType = metadata_id[2]

    token = get_Token(siteNum)
    headers = {
        'Instance': token,
    }
    url = PAsearchSites.getSearchSearchURL(siteNum) + '/v2/releases?type=%s&id=%s' % (sceneType, sceneID)
    Log('---- network1service-update(): sceneURL:               %s' % url)

    req = PAutils.HTTPRequest(url, headers=headers)
    detailsPageElements = req.json()['result'][0]

    # Title
    metadata.title = PAutils.parseTitle(detailsPageElements['title'], siteNum).replace('ï¿½', '\'')
    Log('---- network1service-update(): updating title:         %s' % metadata.title)

    # Summary
    description = None
    if 'description' in detailsPageElements:
        description = detailsPageElements['description']
    elif 'parent' in detailsPageElements:
        if 'description' in detailsPageElements['parent']:
            description = detailsPageElements['parent']['description']

    if description:
        metadata.summary = description

    # Studio
    metadata.studio = PAutils.parseTitle(detailsPageElements['brand'], siteNum)
    Log('---- network1service-update(): studio:                 %s' % metadata.studio)

    # Tagline and Collection(s)
    seriesNames = []

    if 'collections' in detailsPageElements and detailsPageElements['collections']:
        for collection in detailsPageElements['collections']:
            seriesNames.append(collection['name'])
            Log('---- network1service-update(): adding collection:      %s' % collection['name'])

    if 'parent' in detailsPageElements:
        if 'title' in detailsPageElements['parent']:
            seriesNames.append(detailsPageElements['parent']['title'])
            Log('---- network1service-update(): adding collection:      %s' % detailsPageElements['parent']['title'])

    isInCollection = False
    siteName = PAsearchSites.getSearchSiteName(siteNum).lower().replace(' ', '').replace('\'', '')
    for seriesName in seriesNames:
        if seriesName.lower().replace(' ', '').replace('\'', '') == siteName:
            isInCollection = True
            break

    if not isInCollection:
        seriesNames.insert(0, PAsearchSites.getSearchSiteName(siteNum))

    for seriesName in seriesNames:
        metadata.collections.add(seriesName)

    # Release Date
    date_object = parse(detailsPageElements['dateReleased'])
    metadata.originally_available_at = date_object
    metadata.year = metadata.originally_available_at.year

    # Genres
    genres = detailsPageElements['tags']
    for genreLink in genres:
        genreName = genreLink['name']

        movieGenres.addGenre(genreName)
        Log('---- network1service-update(): genres:                 %s' % genreName)

    # Actor(s)
    actors = detailsPageElements['actors']
    for actorLink in actors:
        actorPageURL = PAsearchSites.getSearchSearchURL(siteNum) + '/v1/actors?id=%d' % actorLink['id']

        req = PAutils.HTTPRequest(actorPageURL, headers=headers)
        actorData = req.json()['result'][0]

        actorName = actorData['name']
        actorPhotoURL = ''
        if actorData['images'] and actorData['images']['profile']:
            actorPhotoURL = actorData['images']['profile']['0']['xs']['url']

        movieActors.addActor(actorName, actorPhotoURL)
        Log('---- network1service-update(): actor name:             %s' % actorName)        
        Log('----                         : actor picture:          %s' % actorPhotoURL)

    # Posters
    for imageType in ['poster', 'cover']:
        if imageType in detailsPageElements['images']:
            for image in sorted(detailsPageElements['images'][imageType]):
                if image.isdigit():
                    art.append(detailsPageElements['images'][imageType][image]['xx']['url'])

    Log('---- network1service-update(): Artwork found:          %d' % len(art))
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
                    Log('---- network1service-update(): poster:                 %s' % posterUrl)
                if width > 100 and width > height:
                    # Item is an art item
                    metadata.art[posterUrl] = Proxy.Media(image.content, sort_order=idx)
                    Log('---- network1service-update(): art item:               %s' % posterUrl)
            except:
                pass

    Log('---- network1service-update(): leaving')

    return metadata
