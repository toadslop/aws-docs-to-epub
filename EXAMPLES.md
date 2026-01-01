# AWS Docs to EPUB Converter - Usage Examples

## Quick Start

Convert any AWS Developer Guide to EPUB:

```bash
python aws_docs_to_epub.py <URL>
```

## Real Examples

### 1. AWS Lambda Developer Guide
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
```
- **Pages**: 443
- **Output**: `lambda_dg.epub`
- **Time**: ~4 minutes

### 2. AWS MSK Developer Guide
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
```
- **Pages**: 295
- **Output**: `msk_developerguide.epub`
- **Time**: ~3 minutes

### 3. AWS EKS User Guide
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
```
- **Pages**: ~200
- **Output**: `eks_userguide.epub`
- **Time**: ~2 minutes

### 4. AWS S3 User Guide
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/s3/latest/userguide/Welcome.html
```
- **Output**: `s3_userguide.epub`

### 5. AWS API Gateway Developer Guide
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/apigateway/latest/developerguide/welcome.html
```
- **Pages**: 409
- **Output**: `apigateway_developerguide.epub`

### 6. Custom Output Filename
```bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/dynamodb/latest/developerguide/Introduction.html -o my_dynamodb_guide.epub
```
- **Output**: `my_dynamodb_guide.epub`

## Advanced Usage

### Convert Multiple Guides
```bash
# Create a batch script
cat > convert_all.sh << 'EOF'
#!/bin/bash
python aws_docs_to_epub.py https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
python aws_docs_to_epub.py https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
python aws_docs_to_epub.py https://docs.aws.amazon.com/s3/latest/userguide/Welcome.html
EOF

chmod +x convert_all.sh
./convert_all.sh
```

### Find Documentation URLs

Go to any AWS service documentation page and copy the URL. The script will automatically:
- Detect the service
- Find the table of contents
- Download all pages
- Create a properly formatted EPUB

## Output Format

Generated EPUB files include:
- Complete table of contents
- All documentation pages
- Preserved formatting
- Working internal links
- Proper metadata

## Reading the EPUB Files

Compatible with:
- **macOS**: Apple Books
- **Windows**: Calibre, Adobe Digital Editions
- **Linux**: Calibre, FBReader
- **iOS/Android**: Apple Books, Google Play Books, Amazon Kindle app

## Tips

1. **URL Selection**: You can use the URL of any page in the guide; the script finds all pages automatically
2. **Internet Connection**: Ensure stable internet for large guides
3. **Storage**: Large guides may create 1-5 MB EPUB files
4. **Time**: Processing time is ~0.5 seconds per page plus download time

## Troubleshooting

### Script doesn't recognize URL
Make sure the URL follows the pattern:
`https://docs.aws.amazon.com/<service>/<version>/<guide-type>/<page>.html`

### Slow conversion
This is normal for large guides (400+ pages). The script includes rate limiting to be respectful to AWS servers.

### Missing pages
Some guides may have non-standard structures. Check the console output to see which pages were processed.
