import requests
import config

def get_messybrainz_id(querydata):
    """
    This function queries messybrainz to get a msid according to the 'artist/title' present in the item metadata
    Args:
        querydata: A dictionary containing basic info for one track
                   minimum fields required: [artis, song title]

    Returns:
        msid: string messybrainz id -> if it is found in the messybrainz database
        None: if no reference is fount in messybrainz database
    """
    msurl = config.MESSYBRAINZ_URL+'submit'
    if isinstance(querydata, dict):
        if 'artist' in querydata and 'title' in querydata:
            r = requests.post(msurl, json=[querydata])
            r.raise_for_status()
            responsedata = r.json()
            if 'recording_mbid' in responsedata['payload'][0]['ids'] and 'recording_msid' in responsedata['payload'][0]['ids']:
                if responsedata['payload'][0]['ids']['recording_mbid'] != '':
                    msid = responsedata['payload'][0]['ids']['recording_mbid']
                    id_type = 'mbid'
                elif responsedata['payload'][0]['ids']['recording_msid'] != '':
                    msid = responsedata['payload'][0]['ids']['recording_msid']
                    id_type = 'msid'
                else:
                    msid = None
            return msid, id_type
        else:
            raise TypeError('Bad Request Data')
    else:
        raise TypeError('Input data is not a dictionary')
