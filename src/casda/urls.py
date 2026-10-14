"""Helpers for the download URLs returned by CASDA."""


def encode_query_plus(url):
    """Encode "+" in the query string of a staged CASDA download URL.

    CASDA returns presigned Pawsey object store URLs with the filename in the
    query string (response-content-disposition) without URL encoding. The
    object store decodes "+" in the query string as a space, so the request no
    longer matches the signature and is rejected (403). This affects fields
    with a "+" in their name (e.g. EMU_0251+04A). The path is not changed, as
    "+" is a literal character there.
    """
    if "?" not in url:
        return url
    path, query = url.split("?", 1)
    return f"{path}?{query.replace('+', '%2B')}"
