document.addEventListener("DOMContentLoaded", function () {
  const fileInput = document.getElementById("fileInput");
  const urlInput = document.getElementById("urlInput");
  const convertBtn = document.getElementById("convertBtn");
  const resultText = document.getElementById("resultText");
  const loader = document.getElementById("loader");

  // Hiển thị tên file khi upload
  fileInput.addEventListener("change", function () {
    const fileName = document.getElementById("fileName");
    if (this.files && this.files[0]) {
      fileName.textContent = this.files[0].name;
      fileName.style.color = "var(--text-color)";
      urlInput.disabled = true;
      urlInput.value = "";
    } else {
      fileName.textContent = "";
      urlInput.disabled = false;
    }
  });

  urlInput.addEventListener("input", function () {
    fileInput.disabled = this.value.length > 0;
    fileInput.value = ""; // Clear file input
  });

  // Convert button click handler
  convertBtn.addEventListener("click", async function () {
    const file = fileInput.files[0];
    const url = urlInput.value.trim();

    // Validate input
    if ((!file && !url) || (file && url)) {
      alert("Vui lòng chọn ảnh hoặc nhập URL của ảnh");
      return;
    }

    // Show loading
    loader.style.display = "block";
    resultText.value = "Đang xử lý...";
    convertBtn.disabled = true;

    try {
      const formData = new FormData();
      if (file) {
        formData.append("file", file);
      } else {
        formData.append("image_url", url);
      }

      const response = await fetch("/extract", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      resultText.value = data.text || "Không tìm thấy chữ trong ảnh";
    } catch (error) {
      resultText.value = `Lỗi: ${error.message}`;
      console.error("Error:", error);
    } finally {
      loader.style.display = "none";
      convertBtn.disabled = false;
    }
  });

  // Reset all function
  document.getElementById("refreshAll").addEventListener("click", function () {
    fileInput.value = "";
    urlInput.value = "";
    resultText.value = "";
    fileInput.disabled = false;
    urlInput.disabled = false;
  });
});
