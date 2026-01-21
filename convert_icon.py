from PIL import Image
img = Image.open("microphone.png")
img.save("microphone.ico", format='ICO', sizes=[(256, 256)])
print("Converted to microphone.ico")
