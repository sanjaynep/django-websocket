(function () {
  function scrollChats() {
    document.querySelectorAll(".chat-box").forEach(function (box) {
      box.scrollTop = box.scrollHeight;
    });
  }

  document.querySelectorAll("[data-message-form]").forEach(function (form) {
    form.addEventListener("submit", function () {
      var input = form.querySelector("input[name='content'], input[name='message']");
      var button = form.querySelector("button[type='submit']");
      var status = form.querySelector(".send-status");
      if (!input || !button || !input.value.trim()) return;
      button.disabled = true;
      button.textContent = "Sending...";
      input.value = "";
      input.disabled = true;
      if (status) {
        status.textContent = "Delivering your message...";
        status.classList.add("visible");
      }
    });
  });

  scrollChats();
}());
