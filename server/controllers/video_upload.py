import pathlib

import aiofiles
from dishka.integrations.fastapi import FromDishka
from fastapi import APIRouter, File, HTTPException, Response, UploadFile

from server.algorithms.disk_space_allocator import DiskSpaceAllocator
from server.algorithms.exceptions.invalid_file_format import InvalidFileFormat
from server.algorithms.exceptions.out_of_disk_space import OutOfDiskSpace
from server.algorithms.video_processing import VideoProcessing
from server.controllers.endpoints_base import APIEndpoint


class VideoUploadEndpoint(APIEndpoint):
    def __init__(self, router: APIRouter):
        super().__init__(router)
        self.router.add_api_route(
            "/videos_upload",
            self.upload_page,
            methods=["get"]
        )
        self.router.add_api_route(
            "/videos",
            self.upload_video,
            methods=["post"]
        )

    async def upload_page(self) -> Response:
        return Response(content="""
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>File Upload</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    margin: 0;
                    background-color: #f4f4f9;
                }
                .upload-container {
                    background-color: #fff;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
                }
                input[type="file"] {
                    margin-bottom: 15px;
                }
                button {
                    padding: 10px 20px;
                    background-color: #007bff;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                }
                button:hover {
                    background-color: #0056b3;
                }
            </style>
        </head>
        <body>
        
        <div class="upload-container">
            <h2>Upload a File</h2>
            <form action="/api/videos" method="post" enctype="multipart/form-data">
                <input type="file" name="video_upload" id="fileToUpload" required>
                <br>
                <button type="submit">Upload File</button>
            </form>
        </div>
        
        </body>
        </html>
        """, status_code=200)

    async def upload_video(
        self,
        disk_space_allocator: FromDishka[DiskSpaceAllocator],
        video_upload: UploadFile = File(...),
    ) -> dict[str, str]:
        if video_upload.filename is None or video_upload.size is None:
            raise HTTPException(
                status_code=400,
                detail='Invalid file name or file size is not found, expecting valid upload'
            )

        try:
            async with (
                aiofiles.tempfile.TemporaryDirectory(prefix="hmms_uploads_") as tmp_dir,
                disk_space_allocator.preallocate_disk_space(video_upload.size) as allocated_space
            ):
                temp_file: pathlib.Path = pathlib.Path(tmp_dir) / video_upload.filename
                async with aiofiles.open(temp_file, 'wb') as f:
                    while contents := await video_upload.read(1024 * 1024):
                        await f.write(contents)


                print(temp_file)
                print(
                    VideoProcessing.probe_video(temp_file)
                )

        except InvalidFileFormat:
            raise HTTPException(status_code=400, detail='Invalid file format, expecting video')

        except OutOfDiskSpace as ran_out_of_disk:
            # TODO: add more details about error
            raise HTTPException(status_code=507, detail="Not enough disk space")

        except Exception:
            raise HTTPException(status_code=500, detail='Something went wrong')

        finally:
            await video_upload.close()

        return {"message": f"Successfuly uploaded {video_upload.filename}"}
