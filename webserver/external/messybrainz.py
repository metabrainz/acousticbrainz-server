import requests
import ujson

def get_messybrainz_id(querydata):
    """
    This function queries messybrainz to get a msid according to the 'artist/title' present in the item metadata
    Args:
        querydata: A dictionary containing at least artis and song title

    Returns:
        msid: string messybrainz id -> if it is found in the messybrainz database
        None: if no reference is fount in messybrainz database

    """
    msurl = 'https://messybrainz.org/submit'
    if isinstance(querydata, list):
        if 'artist' in querydata[0].keys() and 'title' in querydata[0].keys():
            jsondata = ujson.dumps(querydata)
            r = requests.post(msurl, data=jsondata)
            if r.status_code == 200:
                #get the correct id
                responsedata = r.json()
                if 'recording_mbid' in responsedata['payload'][0]['ids'].keys() and 'recording_msid' in responsedata['payload'][0]['ids'].keys():
                    if responsedata['payload'][0]['ids']['recording_mbid'] != '':
                        msid = responsedata['payload'][0]['ids']['recording_mbid']
                    elif responsedata['payload'][0]['ids']['recording_msid'] != '':
                        msid = responsedata['payload'][0]['ids']['recording_msid']
                    else:
                        msid = None
                return msid
            else:
                raise TypeError('Request to messybrainz failed with HTTP status code:'+str(r.status_code))
        else:
            raise TypeError('Bad Request Data')
    else:
        raise TypeError('Input data is not a dictionary')
