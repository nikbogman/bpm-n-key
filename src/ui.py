from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import gradio as gr
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.audio_processing import (
    download_audio_from_url,
    get_audio_length,
    get_audio_length_str,
    process_audio,
)
from src.soundcloud import SoundCloudClient, SoundCloudResolver

BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR.parent / "templates"

env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(enabled_extensions=("html",)),
)

results_template = env.get_template("results_stack.html")


def build_ui() -> gr.Blocks:
    requests_session = requests.Session()
    soundcloud_resolver = SoundCloudResolver(SoundCloudClient(requests_session))

    with gr.Blocks() as ui:
        with gr.Row():
            # Left column: input + button + errors
            with gr.Column(scale=1):
                with gr.Row():
                    gr.Markdown(
                        "**Upload an audio file, then press the button to process it.**"
                    )

                audio_path_state = gr.State(None)
                audio_input = gr.Audio(type="filepath", buttons=["play", "upload"])

                url_state = gr.State(None)
                url_input = gr.Textbox(label="Soundcloud URL")

                with gr.Row():
                    clear_button = gr.Button("Clear")
                    process_button = gr.Button(
                        "Process audio", interactive=False, variant="primary"
                    )

                @audio_input.change(
                    inputs=audio_input, outputs=[audio_path_state, process_button]
                )
                def on_audio_input_change(audio_path: Union[str, Path, None]):
                    if not audio_path:
                        return None, gr.update(interactive=False)

                    if isinstance(audio_path, str):
                        audio_path = Path(audio_path)

                    length = get_audio_length(audio_path)
                    if length < 30 or length > 5 * 60:
                        raise gr.Error(
                            f"Audio length {get_audio_length_str(length)} is out of allowed range (30s - 300s)"
                        )

                    return [audio_path, gr.update(interactive=True)]

                @url_input.change(inputs=url_input, outputs=[url_state, process_button])
                def on_url_input(url: str):
                    if url.strip():
                        return [url.strip(), gr.update(interactive=True)]
                    return [None, gr.update(interactive=False)]

            # Right column: results stack
            with gr.Column(scale=1):
                with gr.Row():
                    gr.Markdown("**Processing result**")

                result_output = gr.HTML("")

            history_state = gr.State([])

            def on_process_button_click(
                audio_path: Union[str, Path, None],
                url: Optional[str],
                history: List[Dict[str, Any]],
            ):
                if audio_path and url:
                    raise gr.Error("Provide either file or URL, not both")
                if not audio_path and not url:
                    raise gr.Error("Provide either file or URL")

                result = dict(
                    # get title
                    title=audio_path.name if audio_path else None,
                    source="file" if audio_path else "soundcloud",
                    artwork_url="https://www.americasfinestlabels.com/images/CCS400BL.jpg",
                    url=url if url else None,
                )

                if audio_path:
                    if audio_path.name in [
                        entry.get("title") for entry in history if entry.get("title")
                    ]:
                        return

                    download_path = audio_path

                elif url:
                    if url in [
                        entry.get("url") for entry in history if entry.get("url")
                    ]:
                        return

                    if not soundcloud_resolver.is_soundcloud_url(url):
                        raise gr.Error(
                            "Provided URL is not a valid SoundCloud track URL"
                        )

                    track = soundcloud_resolver.resolve(url)
                    download_path = download_audio_from_url(track["download_url"])
                    result.update(
                        title=track.get("title"),
                        artist=track.get("artist"),
                        artwork_url=track.get("artwork_url"),
                    )

                    if result.get("title") in [
                        entry.get("title") for entry in history if entry.get("title")
                    ]:
                        return
                analysis = process_audio(download_path)

                result["analysis"] = analysis
                new_history = [result] + history

                return (
                    gr.update(value=None),
                    "",
                    results_template.render(entries=new_history),
                    new_history,
                    gr.update(interactive=True),
                )

            process_button.click(
                fn=lambda: gr.update(interactive=False),
                inputs=None,
                outputs=process_button,
            ).then(
                fn=on_process_button_click,
                inputs=[audio_path_state, url_state, history_state],
                outputs=[
                    audio_input,
                    url_input,
                    result_output,
                    history_state,
                    process_button,
                ],
            )

            def clear_ui():
                return (
                    gr.update(value=None),
                    "",
                    None,
                    None,
                    gr.update(interactive=False),
                )

            clear_button.click(
                fn=clear_ui,
                inputs=None,
                outputs=[
                    audio_input,
                    url_input,
                    audio_path_state,
                    url_state,
                    process_button,
                ],
            )

    return ui
