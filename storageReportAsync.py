#!/usr/bin/env python3
from mackee import main, eprint, GetCMS, GetArgs, TimeString, list_to_csv
import sys
import time
from threading import Lock

videosProcessed = 0
counter_lock = Lock()
data_lock = Lock()

row_list = [ ['video_id','delivery_type','master_size','hls_renditions_size','mp4_renditions_size','audio_renditions_size'] ]

def showProgress(progress: int) -> None:
	sys.stderr.write(f'\r{progress} processed...\r')
	sys.stderr.flush()

#===========================================
# function to get size of master
#===========================================
def getMasterStorage(video: dict) -> int:
	masterSize = 0
	response = None

	if(video.get('has_digital_master')):
		try:
			response = GetCMS().GetDigitalMasterInfo(videoID=video.get('id'))
		except Exception as e:
			response = None
			masterSize = -1

		if(response and response.status_code == 200):
			masterSize = response.json().get('size')

	return masterSize

#===========================================
# function to get size of all renditions
#===========================================
def getRenditionSizes(video: dict) -> dict:
	sizes = {
		'hls_size':0,
		'mp4_size':0,
		'audio_size':0
	}

	response = None
	delivery_type = video.get('delivery_type')
	video_id = video.get('id')

	try:
		if(delivery_type == 'static_origin'):
			response = GetCMS().GetRenditionList(videoID=video_id)
		elif(delivery_type == 'dynamic_origin'):
			response = GetCMS().GetDynamicRenditions(videoID=video_id)
	except Exception as e:
		response = None
		sizes = { key:-1 for key in sizes }

	if(response and response.status_code in GetCMS().success_responses):
		renditions = response.json()
		for rendition in renditions:
			size = rendition.get('size')
			# legacy mp4 and hls
			if(rendition.get('video_container') == 'MP4'):
				sizes['mp4_size'] += size
			elif(rendition.get('video_container') == 'M2TS'):
				sizes['hls_size'] += size

			# dyd audio and video
			elif(rendition.get('media_type') == 'audio'):
				sizes['audio_size'] += size
			elif(rendition.get('media_type') == 'video'):
				sizes['hls_size'] += size
		
		# if it's Dynamic Delivery we need to get MP4 sizes from the sources endpoint
		if(delivery_type == 'dynamic_origin' and sizes['mp4_size'] == 0):
			try:
				response = GetCMS().GetVideoSources(videoID=video_id)
			except Exception as e:
				response = None
				sizes['mp4_size'] = -1

			if(response and response.status_code in GetCMS().success_responses):
				renditions = response.json()
				dyd_mp4 = set()
				for rendition in renditions:
					if(rendition.get('container') == 'MP4'):
						dyd_mp4.add(rendition.get('size'))
				
				for size in dyd_mp4:
					if(size):
						sizes['mp4_size'] += size

	return sizes

#===========================================
# callback getting storage sizes
#===========================================
def findStorageSize(video: dict) -> None:
	global videosProcessed

	row = [ video.get('id'), video.get('delivery_type') ]

	shared = video.get('sharing')
	if(shared and shared.get('by_external_acct')):
		row.extend( [0 for _ in range(len(row_list[0])-len(row))] )
	else:
		row.append( getMasterStorage(video) )
		sizes = getRenditionSizes(video)
		row.extend( [sizes["hls_size"], sizes["mp4_size"], sizes["audio_size"]] )

	# add a new row to the CSV data
	with data_lock:
		row_list.append(row)

	# increase processed videos counter
	with counter_lock:
		videosProcessed += 1

	# display counter every 100 videos
	if(videosProcessed%100==0):
		showProgress(videosProcessed)

#===========================================
# only run code if it's not imported
#===========================================
if __name__ == '__main__':
	s = time.perf_counter()
	main(findStorageSize)
	showProgress(videosProcessed)

	#write list to file
	list_to_csv(row_list, GetArgs().o)

	elapsed = time.perf_counter() - s
	eprint(f"\n{__file__} executed in {TimeString.from_seconds(elapsed)}.")	
