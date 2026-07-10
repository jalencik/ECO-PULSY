/* Trees page: the little "what do N trees actually do" calculator.
 *
 * Assumption shown to the user on the page: a healthy urban tree
 * absorbs roughly 22 kg of CO2 per year once established (a widely
 * used planning figure, e.g. FAO/iTree urban forestry material), and
 * an average passenger car emits about 4.6 tonnes of CO2 per year.
 * This is an illustration, not an offset claim - the note under the
 * calculator says exactly that.
 */
(function () {
  "use strict";

  var input = document.getElementById("tree-calc-input");
  var co2Out = document.getElementById("tree-calc-co2");
  var carsOut = document.getElementById("tree-calc-cars");
  if (!input || !co2Out || !carsOut) return;

  var CO2_PER_TREE_KG = 22;
  var CAR_KG_PER_YEAR = 4600;

  function update() {
    var trees = parseInt(input.value, 10);
    if (isNaN(trees) || trees < 0) trees = 0;
    var kg = trees * CO2_PER_TREE_KG;
    co2Out.textContent = kg >= 10000
      ? (kg / 1000).toFixed(1).replace(/\.0$/, "") + " t"
      : kg.toLocaleString("en-US").replace(/,/g, " ");
    carsOut.textContent = (kg / CAR_KG_PER_YEAR).toFixed(kg / CAR_KG_PER_YEAR >= 10 ? 0 : 2);
  }

  input.addEventListener("input", update);
  update();
})();
