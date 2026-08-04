/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package pointofsale;

/**
 *
 * @author kim2
 */
public class SaleLineItem {
    private Item item;
    private int quantity;

    public SaleLineItem(Item item, int quantity) {
        this.item = item;
        this.quantity = quantity;
    }
    
    public double getSubTotal() {
        return item.getPrice() * quantity;
    }
    
    public String getItemName() {
        return item.getName();
    }
    
    public int getQuantity() {
        return quantity;
    }
}