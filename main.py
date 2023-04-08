from pytube import YouTube, request
from tkinter import *
from tkinter import ttk
from tkinter.filedialog import *
import re
import threading
from demucs.separate import load_track
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import save_audio
from pathlib import Path
import torch as th

filesize = 0
SR = 44100
STEREO = 2
DEFAULT_MODEL = "htdemucs"


def download_audio(url, filelocation):
    global is_paused, is_cancelled, filesize, downloaded
    download_audio_button["state"] = "disabled"
    try:
        progress["text"] = "Connecting ..."
        yt = YouTube(url)
        stream = yt.streams.filter(only_audio=True).first()
        filesize = stream.filesize
        string = "".join([i for i in re.findall("[\w +/.]", yt.title) if i.isalpha()])
        filename = filelocation + "/" + string + ".mp3"
        with open(filename, "wb") as f:
            is_paused = is_cancelled = False
            stream = request.stream(stream.url)
            downloaded = 0
            while True:
                if is_cancelled:
                    progress["text"] = "Download cancelled"
                    break
                if is_paused:
                    continue
                chunk = next(stream, None)
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress["text"] = f"Downloaded {downloaded} / {filesize}"
                else:
                    # no more data
                    break
        progress["text"] = "Audio Download completed! Separating ..."
        separate_audio(filename, filelocation)
        progress["text"] = "Done"

    except Exception as e:
        print(e)
    download_audio_button["state"] = "normal"


def separate_audio(input_file, output_dir):
    model = get_model(DEFAULT_MODEL)

    wav = load_track(input_file, STEREO, SR)
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()
    sources = apply_model(model, wav[None], progress=True)[0]
    sources = sources * ref.std() + ref.mean()

    kwargs = {
        "samplerate": model.samplerate,
        "bitrate": 320,
        "clip": "rescale",
        "as_float": False,
        "bits_per_sample": 16,
    }

    sources = list(sources)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    progress["text"] = f"Separated tracks will be stored in {out.resolve()}."

    input_file_path = Path(input_file)

    filename = "{track}_{stem}.{ext}"
    stem = out / filename.format(
        track=input_file_path.name.rsplit(".", 1)[0],
        ext=input_file_path.name.rsplit(".", 1)[-1],
        stem="vocals",
    )
    stem.parent.mkdir(parents=True, exist_ok=True)
    save_audio(sources.pop(model.sources.index("vocals")), str(stem), **kwargs)
    other_stem = th.zeros_like(sources[0])
    for i in sources:
        other_stem += i

    stem = out / filename.format(
        track=input_file_path.name.rsplit(".", 1)[0],
        ext=input_file_path.name.rsplit(".", 1)[-1],
        stem="no_" + "vocals",
    )
    stem.parent.mkdir(parents=True, exist_ok=True)
    save_audio(other_stem, str(stem), **kwargs)


def start_audio_download():
    filelocation = askdirectory()
    threading.Thread(
        target=download_audio, args=(url_entry.get(), filelocation), daemon=True
    ).start()


root = Tk()
root.title("Youtube Audio Separator")
root.geometry("700x180+250+50")

url_entry = Entry(root, justify=CENTER, bd=5, fg="green")
url_entry.pack(side=TOP, fill=X, padx=10)
url_entry.focus()

download_audio_button = Button(
    root,
    text="Download Audio",
    width=20,
    command=start_audio_download,
    font="verdana",
    relief="ridge",
    bd=5,
    bg="#f5f5f5",
    fg="black",
)
download_audio_button.pack(side=TOP, pady=20)

progress = Label(root)
progress.pack(side=TOP)

root.mainloop()
