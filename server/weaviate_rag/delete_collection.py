from app.services.weaviate_setup import client

client.collections.delete("LectureChunk")
print("✅ Deleted LectureChunk collection")

client.close()  