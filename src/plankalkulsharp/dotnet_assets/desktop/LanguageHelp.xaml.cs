using System.Windows.Controls;
using System.Windows.Documents;

namespace PlankalkulMachine;

public partial class LanguageHelp : UserControl
{
    public LanguageHelp()
    {
        InitializeComponent();
        foreach (var section in Reader.Document.Blocks.OfType<Section>())
            Contents.Items.Add(new ListBoxItem { Content = section.Tag, Tag = section });
    }

    void Search_Changed(object sender, TextChangedEventArgs e)
    {
        if (Contents is null || Reader is null) return;
        string query = TopicSearch.Text.Trim();
        int count = 0;
        foreach (ListBoxItem item in Contents.Items)
        {
            var section = (Section)item.Tag;
            string text = new TextRange(section.ContentStart, section.ContentEnd).Text;
            bool matches = text.Contains(query, StringComparison.OrdinalIgnoreCase)
                || (section.Tag?.ToString() ?? "").Contains(query, StringComparison.OrdinalIgnoreCase);
            item.Visibility = matches ? System.Windows.Visibility.Visible : System.Windows.Visibility.Collapsed;
            if (matches) count++;
        }
        SearchStatus.Text = count == 0 ? "Ничего не найдено. Попробуйте название конструкции: W, FIN, список." : $"Тем: {count}";
        Contents.SelectedItem = Contents.Items.OfType<ListBoxItem>().FirstOrDefault(i => i.Visibility == System.Windows.Visibility.Visible);
    }

    void Topic_Selected(object sender, SelectionChangedEventArgs e)
    {
        if (Contents.SelectedItem is ListBoxItem { Tag: Section section }) section.BringIntoView();
    }
}
