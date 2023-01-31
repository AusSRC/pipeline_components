from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy_healpix import HEALPix
from astropy.io import fits




def name(fitsimage, prefix, cenfreq, tileID, version='v1'):

    """
    Setting up the name to be used for tiles. The script reads
    the bmaj and stokes from the fits header. The rest of the parameters are 
    flexible to change.
    
    fitsimage: tile image
    prefix   : prefix to use. E.g. PSM for full survey,
               PSM_pilot1 for POSSUM pilot 1
               PSM_pilot2 for POSSUM pilot 2
    cenfreq  : Central frequency (for band 1 we set it to 944MHz,
               for band 2 1296MHz)
    tileID   : tile pixel (Healpix pixel)
    
    version  : version of the output product. Version 1 is v1, version is v2,
               and so forth.
    
    """

    print('>>> Reading the header from the image %s'%fitsimage)
    hdr = fits.getheader(fitsimage)
    
    #get bmaj.
    bmaj = hdr['BMAJ'] * 3600.0
    
    # extract stokes parameter. It can be in either the 3rd or fourth axis.
    if hdr['CTYPE3'] == 'STOKES':
        stokes = hdr['CRVAL3']
       
    if hdr['CTYPE4'] == 'STOKES':
        stokes = hdr['CRVAL4']
      
    else:
        sys.exit('>>> Cannot find Stokes axis on the 3rd/4th axis')
        
    # stokes I=1, Q=2, U=3 and 4=V    
    if int(stokes) == 1:
        stokesid = 'i'
       
    if int(stokes) == 2:
        stokesid = 'q'
        
    if int(stokes) == 3:
        stokesid = 'u'

    if int(stokes) == 4:
        stokesid = 'v'
        
    # define the healpix grid
    hp = HEALPix(nside=32, order='ring', frame='icrs')

    # extract the RA and DEC for a specific pixel 
    center = hp.healpix_to_lonlat(tileID) * u.deg
    RA, DEC = center.value
 
    c = SkyCoord(ra=RA*u.degree, dec=DEC*u.degree, frame='icrs')

    h, hm, hs = c.ra.hms
    hm = '%d%d'%(h, round(hm + (hs/60.0)))

    d, dm, ds = c.dec.dms
    dm = '%d%d'%(d, round(abs(dm) + (abs(dm)/60.0)))

    RADEC = '%s%s'%(hm, dm)
    
    outname = prefix +'_%s'%cenfreq+'_%.1f'%bmaj+'_%s'%(RADEC)+'_%s'%stokesid+'_%s'%version+'.fits'
    
    print('>>> The tile outname is %s'%outname)
    
    
    
    
name(fitsimage='EMU-2154-55-10978.fits', prefix='PSM', cenfreq='944MHz', tileID=10978, version='v1')  

    


