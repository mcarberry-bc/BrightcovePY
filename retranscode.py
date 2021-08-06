#!/usr/bin/env python3
from mackee import main, get_cms, get_di

#===================================================
# retranscode video and use MP4 if it has no master
#===================================================
def retranscode(video: dict):
    """
    This will retranscode a video using the digital master if it exists.
    If no master exists it will use the best quality MP4.
    """
    # get some basic info about the video
    video_id = str(video.get('id'))
    delivery_type = video.get('delivery_type')
    has_master = video.get('has_digital_master')
    is_shared = video.get('sharing')

    # if it's not legacy or dynamic delivery we bail
    if delivery_type not in ['static_origin', 'dynamic_origin']:
        print(f'{video_id}: can not be retranscoded (delivery type: {delivery_type})')
        return

    # if it's a shared video we also bail
    if is_shared and is_shared.get('by_external_acct'):
        print(f'{video_id}: can not be retranscoded (shared into account)')
        return

    # retranscode specific settings
    ingest_profile = 'multi-platform-extended-static-with-mp4'
    priority = 'low'
    capture_images = False

    # if it has a master then use that for retranscode
    if has_master:
        print(f'{video_id}: retranscoding using digital master -> {get_di().RetranscodeVideo(video_id=video_id, profile_id=ingest_profile,capture_images=capture_images, priority_queue=priority).status_code}')

    # otherwise try to find a high resolution MP4 rendition and use that
    else:
        # get sources for the video and try to find the biggest MP4 video
        source_url, source_w, source_h = '', 0, 0
        source_list = get_cms().GetVideoSources(video_id=video_id).json()
        for source in source_list:
            if source.get('container') == 'MP4':
                w, h = source.get('width', 0), source.get('height', 0)
                if w>source_w: # checking w/h to avoid error by audio only renditions
                    if source_url := source.get('src'):
                        source_w, source_h = w, h

        # if a source was found download it, using the video ID as filename
        if source_url:
            print(f'{video_id}: retranscoding using highest resolution MP4 ({source_w}x{source_h}) -> {get_di().SubmitIngest(video_id=video_id, source_url=source_url, profile_id=ingest_profile,capture_images=capture_images, priority_queue=priority).status_code}')

        else:
            print(f'{video_id}: can not be retranscoded (no master or MP4 video rendition)')

#===================================================
# only run code if it's not imported
#===================================================
if __name__ == '__main__':
    main(retranscode)
