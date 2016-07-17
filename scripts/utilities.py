import os
import urllib2

def curl( url, data = None, authToken = None ):

	if data is not None:
		req = urllib2.Request( url, data )
	else:
		req = urllib2.Request( url )

	if authToken is not None:
		req.add_header( 'Authorization', 'Basic %s'%authToken )

	response = urllib2.urlopen( req )
	res = response.read()
	return res

def info(title):
    print title
    if hasattr(os, 'getppid'):  # only available on Unix
        print 'parent process:', os.getppid()
    print 'process id:', os.getpid()

if __name__ == '__main__':
	info('utilities')
	p = Process(target=f, args=('bob',))
	p.start()
	p.join()