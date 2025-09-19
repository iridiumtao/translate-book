# Translate books with Gemini

This project harnesses the power of Google's Gemini Pro LLM to translate eBooks from any language into your preferred language, maintaining the integrity and structure of the original content. Imagine having access to a vast world of literature, regardless of the original language, right at your fingertips.

This tool not only translates the text but also carefully compiles each element of the eBook – chapters, footnotes, and all – into a perfectly formatted EPUB file. We use the `gemini-2.5-pro` model by default to ensure high-quality translations.

## Features

- **High-Quality Translation**: Utilizes the powerful `gemini-2.5-pro` model for accurate and nuanced translations.
- **Concurrent Translations**: Processes multiple book chapters and chunks in parallel, significantly speeding up the translation of large books.
- **Rate Limit Handling**: Automatically retries failed requests when API rate limits are hit, ensuring a smooth and resilient translation process.
- **Chapter Selection**: Allows you to translate specific chapters of a book.
- **Preserves Formatting**: Keeps the original HTML tags and structure of the eBook intact.

## 🛠️ Installation

To install the necessary components for our project, follow these simple steps:

```bash
pip install -r requirements.txt
cp config.yaml.example config.yaml
```

Remember to add your Google AI API key to `config.yaml`.


## 🎮 Usage

Our script comes with a variety of parameters to suit your needs. Here's how you can make the most out of it:

### Show Chapters

Before diving into translation, it's recommended to use the `show-chapters` mode to review the structure of your book:

```bash
python main.py show-chapters --input yourbook.epub
```

This command will display all the chapters, helping you to plan your translation process effectively.

### Translate Mode

#### Basic Usage

To translate a book from EN to zh-TW, use the following command:

```bash
python main.py translate --input yourbook.epub --output translatedbook.epub --config config.yaml --from-lang English --to-lang 台灣繁體中文 --n-worker 2
```

#### Advanced Usage

For more specific needs, such as translating from chapter 13 to chapter 37 from English to Polish with high concurrency, use:

```bash
python main.py translate --input yourbook.epub --output translatedbook.epub --config config.yaml --from-chapter 13 --to-chapter 37 --from-lang English --to-lang 台灣繁體中文 --n-worker 30
```

### Concurrency and Performance

The `--n-worker` parameter sets the number of parallel threads for translating chunks. A higher number can significantly speed up the translation process. For users on the Gemini API Tier 1 (150 RPM) plan, you can set this value to 30 or even higher to maximize throughput.

The script also has a built-in retry mechanism. If you hit the API rate limit, it will automatically wait for one minute and then retry the request, making the translation process resilient to interruptions.

See [Gemini API Rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)


## Converting from AZW3 to EPUB

For books in AZW3 format (Amazon Kindle), use Calibre (https://calibre-ebook.com) to convert them to EPUB before using this tool.


## DRM (Digital Rights Management)

Amazon eBooks (AZW3 format) are encrypted with your device's serial number. To decrypt these books, use the DeDRM tool (https://dedrm.com). You can find your Kindle's serial number at https://www.amazon.com/hz/mycd/digital-console/alldevices.


## 🤝 Contributing

We warmly welcome contributions to this project! Your insights and improvements are invaluable. Currently, we're particularly interested in contributions in the following areas:

- Support for other eBook formats: AZW3, MOBI, PDF.
- Integration of a built-in DeDRM tool

Join us in breaking down language barriers in literature and enhancing the accessibility of eBooks worldwide!

## License

This project is licensed under the MIT License. See the [LICENSE.md](LICENSE.md) file for details.
