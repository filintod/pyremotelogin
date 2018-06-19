from fdutils.web.web import download_resources, HashedURLResource

nhtsa_zip = 'https://www-odi.nhtsa.dot.gov/downloads/folders/Investigations/FLAT_INV.zip'

#%%timeit -r 1
electron_zip = 'https://github.com/electron/electron/releases/download/v1.8.2-beta.1/electron-v1.8.2-beta.1-darwin-x64-symbols.zip'
electron_zip_hash = 'ec2bfe1ebb83f2cb79af302d36c5f68e33de238ba7538b4ed51ec1507af9a806'

from fdutils.web import download_resources

r = HashedURLResource(electron_zip, electron_zip_hash, 'sha256')
#download_resources(r, unzip=True, timestamp=False)
download_resources('http://prdownloads.sourceforge.net/weka/uci-20070111.tar.gz', unzip=True)
