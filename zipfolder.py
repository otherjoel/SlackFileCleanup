import zipfile
import os
import statistics

DEBUG = True

def tell_last(iterable):
    """A wrapper for iterables, allowing the caller to know whether they are
    on the last item in the list. (Python has a `first` but not a `last`!)
    """
    # Get an iterator and pull the first value.
    it = iter(iterable)
    prev = next(it)
    # Run the iterator to exhaustion (starting from the second value).
    for val in it:
        # Report the *previous* value (more to come).
        yield prev, False
        prev = val
    # Report the last value.
    yield prev, True

def max_mean_filesizes(folder):
    """Returns two values, max and median size of files in directory, in bytes."""
    
    if not os.path.isdir(folder):
        raise FileNotFoundError("%s is not a folder!" % folder_path)
    
    file_sizes = []
    
    for basename in os.listdir(folder):
        filename = os.path.join(folder, basename)
        if os.path.isfile(filename):
            file_sizes.append(os.path.getsize(filename))
    
    return max(file_sizes), statistics.median(file_sizes)

def zip_folder(folder_path, zipfile_prefix, rough_size_limit_mb=None):
    """Creates zip archive(s) of all files in a folder (non-recursive!)
    Can split the archive into multiple standalone .zip files in order
    to keep them manageable (e.g. for downloading).
    
    Parameters
    ----------
    folder_path : str
        The path to the folder containing the files you want zipped. All
        files will be zipped. Any subfolders will be ignored!
    
    zipfile_prefix : str
        The prefix to use when creating .zip files (such as a YYYY-MM date). 
        This can include a relative or absolute path. If multiple files are
        created, the suffix of '_001', '_002' will be added before the .zip
        extension.
        
    rough_size_limit_mb : int, optional
        How big each zip file should be allowed to grow before closing it and
        starting a new one. If supplied, it MUST be >= the size of the biggest
        file plus the median file size, to prevent weirdness. It's "rough"
        because the first file to bump the size over the limit will be left
        in the zip file and a new one started for the next file; so the limit
        will in practice be exceeded by roughly the size of any particular
        file in the folder (after compression). If omitted, the function will
        put everything in one zip file.
        
    Returns
    -------
    archive_list : list of str
        A list of all the zip files (with absolute paths) created by the function.
    """
    
    if not os.path.isdir(folder_path):
        raise FileNotFoundError("%s is not a folder!" % folder_path)
    
    path_to_here = os.path.abspath(os.path.dirname(__file__))
    
    if rough_size_limit_mb is not None:
        biggest_filesize, median_filesize = max_mean_filesizes(folder_path)
        min_mb_limit = round((biggest_filesize + median_filesize) / 1000000,0)
        
        if rough_size_limit_mb < min_mb_limit:
            raise ValueError("rough_size_limit must be at least %s MB for this folder" \
                             % min_limit)
        
        archive_split_count = 1
        zipfile_basename = zipfile_prefix + '_001'
        rough_size_limit_bytes = rough_size_limit_mb * 1000000
    else:
        zipfile_basename = zipfile_prefix
    
    archive_list = [ os.path.join(path_to_here, zipfile_basename + '.zip') ]

    zip_archive = zipfile.ZipFile(archive_list[0], mode='w') 
    compressed_total_bytes = 0
    
    for filename, is_last_file in tell_last(os.listdir(folder_path)):
        full_file_path = os.path.join(folder_path, filename)

        if os.path.isfile(full_file_path):
            zip_archive.write(full_file_path, arcname=filename,
                              compress_type=zipfile.ZIP_DEFLATED)
            
            zipped_info = zip_archive.getinfo(filename)
            file_compressed = zipped_info.compress_size
            file_size = zipped_info.file_size
            
            compressed_total_bytes += file_compressed
            
            if DEBUG:
                print("Zipped %s, actual/compressed size: %s/%s bytes, total %s" % \
                      (full_file_path, file_size, file_compressed, compressed_total_bytes))

            if rough_size_limit_mb is not None:
                if compressed_total_bytes >= rough_size_limit_bytes and not is_last_file:
                    archive_split_count += 1
                    zipfile_basename = zipfile_prefix + "_{0:0>3}".format(archive_split_count)
                
                    zip_archive.close()
                    new_zip_name = os.path.join(path_to_here, zipfile_basename + '.zip')
                    zip_archive = zipfile.ZipFile(new_zip_name, mode='w')
                    compressed_total_bytes = 0
                    archive_list.append(new_zip_name)

                    if DEBUG:
                        print("Created %s" % new_zip_name)
                
    zip_archive.close()
    
    return archive_list