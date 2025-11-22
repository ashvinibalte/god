documents = [doc.strip().strip('"').strip("'") for doc in content.replace("\n", ",").split(',')]
