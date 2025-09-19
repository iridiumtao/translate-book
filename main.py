import argparse, \
       re, \
       yaml, \
       concurrent.futures
import time

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import google.generativeai as genai
import google.api_core.exceptions
from tqdm import tqdm
import signal


def read_config(config_file):
    with open(config_file, 'r') as f:
        config = yaml.load(f, Loader=yaml.FullLoader)

    return config


def split_html(html_str, max_chunk_size=10000):
    soup = BeautifulSoup(html_str, 'html.parser')
    
    # It's better to work with the body tag, but if it's not there, work with the whole soup
    root = soup.body if soup.body else soup

    chunks = []
    current_chunk = ""

    for element in list(root.children):
        element_html = str(element)
        if len(current_chunk) + len(element_html) > max_chunk_size and current_chunk:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += element_html
    
    if current_chunk:
        chunks.append(current_chunk)

    if not chunks and html_str:
        chunks.append(html_str)

    return chunks


def system_prompt(from_lang, to_lang):
    return f"You are an {from_lang}-to-{to_lang} translator. Keep all special characters and HTML tags as in the source text. Return only {to_lang} translation."


def translate_chunk(model, text, from_lang='EN', to_lang='PL'):
    retries = 5
    delay = 60  # 1 minute

    for attempt in range(retries):
        try:
            response = model.generate_content(
                system_prompt(from_lang, to_lang) + text
            )
            return response.text
        except google.api_core.exceptions.ResourceExhausted as e:
            if attempt < retries - 1:
                print(f"Rate limit exceeded. Attempt {attempt + 1}/{retries} failed. Waiting for {delay} seconds before retrying...")
                time.sleep(delay)
            else:
                print(f"Rate limit exceeded. All {retries} attempts failed.")
                raise e
        except Exception as e:
            print(f"An unexpected error occurred while translating chunk: {e}")
            raise e


def translate(client, input_epub_path, output_epub_path, from_chapter=0, to_chapter=9999, from_lang='EN', to_lang='PL', n_worker=5):
    book = epub.read_epub(input_epub_path)

    # 1. Collect all chapters to be translated
    chapters_to_translate = []
    all_items = list(book.get_items())
    
    current_chapter_num = 1
    for item in all_items:
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            if from_chapter <= current_chapter_num <= to_chapter:
                chapters_to_translate.append({
                    "item": item,
                    "original_content": item.content,
                    "chapter_num": current_chapter_num
                })
            current_chapter_num += 1

    chapters_count = len([i for i in all_items if i.get_type() == ebooklib.ITEM_DOCUMENT])
    print(f"Found {len(chapters_to_translate)} chapters to translate out of {chapters_count}.")

    # 2. Create a flat list of all chunks from all chapters
    all_chunks = []
    chunk_to_chapter_map = []
    chapter_chunks_info = []
    model = client.GenerativeModel('gemini-2.5-pro')

    for i, chapter_data in enumerate(chapters_to_translate):
        soup = BeautifulSoup(chapter_data["original_content"], 'html.parser')
        chunks = split_html(str(soup))
        num_chunks = len(chunks)
        chapter_chunks_info.append(num_chunks)
        
        for j, chunk_content in enumerate(chunks):
            all_chunks.append(chunk_content)
            chunk_to_chapter_map.append({
                "chapter_index": i, 
                "chunk_index_in_chapter": j
            })
    
    print(f"Total chunks to translate: {len(all_chunks)}")

    # 3. Translate all chunks concurrently
    translated_chunks_flat = [None] * len(all_chunks)
    with concurrent.futures.ThreadPoolExecutor(max_workers=n_worker) as executor:
        future_to_chunk_index = {
            executor.submit(translate_chunk, model, chunk, from_lang, to_lang): i 
            for i, chunk in enumerate(all_chunks)
        }
        
        for future in tqdm(concurrent.futures.as_completed(future_to_chunk_index), total=len(all_chunks), desc="Translating all chunks"):
            flat_chunk_index = future_to_chunk_index[future]
            try:
                translated_chunks_flat[flat_chunk_index] = future.result()
            except Exception as exc:
                chapter_info = chunk_to_chapter_map[flat_chunk_index]
                chapter_index = chapter_info["chapter_index"]
                chapter_num = chapters_to_translate[chapter_index]["chapter_num"]
                print(f'Chunk {flat_chunk_index} (from chapter {chapter_num}) generated an exception: {exc}')

    # 4. Reassemble chapters
    translated_chapters_chunks = []
    start_index = 0
    for num_chunks in chapter_chunks_info:
        end_index = start_index + num_chunks
        translated_chapters_chunks.append(translated_chunks_flat[start_index:end_index])
        start_index = end_index

    for i, chapter_data in enumerate(chapters_to_translate):
        translated_content = ' '.join(c for c in translated_chapters_chunks[i] if c is not None)
        if translated_content:
            chapter_data["item"].content = translated_content.encode('utf-8')

    epub.write_epub(output_epub_path, book, {})

def show_chapters(input_epub_path):
    book = epub.read_epub(input_epub_path)

    current_chapter = 1
    chapters_count = len([i for i in book.get_items() if i.get_type() == ebooklib.ITEM_DOCUMENT])

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            print("▶️  Chapter %d/%d (%d characters)" % (current_chapter, chapters_count, len(item.content)))
            soup = BeautifulSoup(item.content, 'html.parser')
            chapter_beginning = soup.text[0:250]
            chapter_beginning = re.sub(r'\n{2,}', '\n', chapter_beginning)
            print(chapter_beginning + "\n\n")

            current_chapter += 1



if __name__ == "__main__":
    # Graceful shutdown
    def signal_handler(sig, frame):
        print('You pressed Ctrl+C! Shutting down gracefully.')
        # Here you can add any cleanup code you need
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Create the top-level parser
    parser = argparse.ArgumentParser(description='App to translate or show chapters of a book.')
    subparsers = parser.add_subparsers(dest='mode', help='Mode of operation.')

    # Create the parser for the "translate" mode
    parser_translate = subparsers.add_parser('translate', help='Translate a book.')
    parser_translate.add_argument('--input', required=True, help='Input file path.')
    parser_translate.add_argument('--output', required=True, help='Output file path.')
    parser_translate.add_argument('--config', required=True, help='Configuration file path.')
    parser_translate.add_argument('--from-chapter', type=int, help='Starting chapter for translation.')
    parser_translate.add_argument('--to-chapter', type=int, help='Ending chapter for translation.')
    parser_translate.add_argument('--from-lang', help='Source language.', default='EN')
    parser_translate.add_argument('--to-lang', help='Target language.', default='PL')
    parser_translate.add_argument('--n-worker', type=int, help='Number of workers for parallel processing.', default=5)

    # Create the parser for the "show-chapters" mode
    parser_show = subparsers.add_parser('show-chapters', help='Show the list of chapters.')
    parser_show.add_argument('--input', required=True, help='Input file path.')

    # Parse the arguments
    args = parser.parse_args()

    # Call the appropriate function based on the mode
    if args.mode == 'translate':
        config = read_config(args.config)
        from_chapter = int(args.from_chapter) if args.from_chapter else 0
        to_chapter = int(args.to_chapter) if args.to_chapter else 9999
        from_lang = args.from_lang
        to_lang = args.to_lang
        n_worker = args.n_worker
        genai.configure(api_key=config['gemini']['api_key'])

        translate(genai, args.input, args.output, from_chapter, to_chapter, from_lang, to_lang, n_worker)

    elif args.mode == 'show-chapters':
        show_chapters(args.input)

    else:
        parser.print_help()
